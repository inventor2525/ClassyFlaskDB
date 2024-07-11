from sqlalchemy import create_engine, Table, Column, Integer, String, Float, DateTime, Boolean, select, MetaData
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, Type, List, Generic, TypeVar, Iterator, Optional
from dataclasses import dataclass, field, Field, MISSING
from datetime import datetime

from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.StorageEngine import StorageEngine, TranscoderCollection, CFInstance
from ClassyFlaskDB.new.Transcoder import Transcoder, LazyLoadingTranscoder
from ClassyFlaskDB.new.Args import MergeArgs, MergePath, SetupArgs, DecodeArgs
from ClassyFlaskDB.new.ClassInfo import ClassInfo
from ClassyFlaskDB.new.Types import Interface, BasicType, ContextType

from sqlalchemy.orm import Session

class SQLMergeArgs(MergeArgs):
    def __init__(self, *args, session: Session, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    def new(self, field: Field):
        return SQLMergeArgs(
            context=self.context,
            path=MergePath(parentObj=self.path.parentObj, fieldOnParent=field),
            encodes=self.encodes,  # Use the same encodes dictionary
            is_dirty=self.is_dirty,
            storage_engine=self.storage_engine,
            session=self.session
        )

T = TypeVar('T')
class SQLAlchemyStorageEngine(StorageEngine):
    def __init__(self, connection_string: str, transcoder_collection: TranscoderCollection, data_decorator: DATADecorator):
        super().__init__()
        self.engine = create_engine(connection_string)
        self.session_maker = sessionmaker(bind=self.engine)
        self.metadata = MetaData()
        self.metadata.reflect(bind=self.engine)
        self.transcoders = transcoder_collection.transcoders
        self.data_decorator = data_decorator
        
        self.data_decorator.finalize(self)
        self.setup(self.data_decorator)

    def setup(self, data_decorator: DATADecorator):
        for cls in data_decorator.registry.values():
            class_info = ClassInfo.get(cls)
            setup_args = SetupArgs(storage_engine=self, class_info=class_info)
            transcoder = self.get_transcoder_type(class_info, None)
            transcoder.setup(setup_args, None)

        self.metadata.create_all(self.engine)

    def merge(self, obj: Any, persist: bool = False):
        context = self.context if persist else {}
        with self.session_maker() as session:
            merge_args = SQLMergeArgs(
                context=context,
                path=MergePath(parentObj=None, fieldOnParent=None),
                encodes={},
                is_dirty={},
                storage_engine=self,
                session=session
            )
            transcoder = self.get_transcoder_type(ClassInfo.get(type(obj)), None)
            transcoder.merge(merge_args, obj)
            session.commit()

    def get_table_name(self, cls: Type) -> str:
        return f"obj_{cls.__name__}"

    def get_transcoder_type(self, class_info: ClassInfo, field: field = None) -> Type[Transcoder]:
        for transcoder in self.transcoders:
            try:
                if transcoder.validate(class_info, field):
                    return transcoder
            except Exception:
                # If validation fails for any reason, consider the transcoder invalid
                continue
        raise ValueError(f"No suitable transcoder found for {class_info.cls.__name__}.{field.name if field else ''}")

    def query(self, cls: Type[T]) -> 'SQLAlchemyStorageEngineQuery[T]':
        return SQLAlchemyStorageEngineQuery(self, cls)

T = TypeVar('T')
class SQLAlchemyStorageEngineQuery(Generic[T]):
    def __init__(self, storage_engine: SQLAlchemyStorageEngine, cls: Type[T]):
        self.storage_engine = storage_engine
        self.cls = cls
        self.table = storage_engine.metadata.tables[storage_engine.get_table_name(cls)]
        self.query = select(self.table)
        self.transcoder:LazyLoadingTranscoder = storage_engine.get_transcoder_type(ClassInfo.get(cls), None)
        if not issubclass(self.transcoder, LazyLoadingTranscoder):
            raise ValueError(f"Transcoder for {cls} does not support lazy loading")

    def filter_by_id(self, id_value: Any) -> T:
        class_info = ClassInfo.get(self.cls)
        primary_key_name = class_info.primary_key_name
        self.query = self.query.where(getattr(self.table.c, primary_key_name) == id_value)
        
        # Check context first
        context_obj = self.storage_engine.context.get(self.cls, {}).get(id_value, MISSING)
        if context_obj is not MISSING:
            return context_obj

        with self.storage_engine.session_maker() as session:
            result = session.execute(self.query).first()
            if result:
                encoded_values = result._asdict()
                obj_id = encoded_values[ClassInfo.get(self.cls).primary_key_name]
                
                # Check context first
                context_obj = self.storage_engine.context.get(self.cls, {}).get(obj_id, MISSING)
                if context_obj is not MISSING:
                    return context_obj
                else:
                    return self._create_lazy_instance(encoded_values)
            return None

    def all(self) -> Iterator[T]:
        with self.storage_engine.session_maker() as session:
            results = session.execute(self.query)
            for row in results:
                encoded_values = row._asdict()
                obj_id = encoded_values[ClassInfo.get(self.cls).primary_key_name]
                
                # Check context first
                context_obj = self.storage_engine.context.get(self.cls, {}).get(obj_id, MISSING)
                if context_obj is not MISSING:
                    yield context_obj
                else:
                    yield self._create_lazy_instance(encoded_values)

    def _create_lazy_instance(self, encoded_values: Dict[str, Any]) -> T:
        instance = self.transcoder.create_lazy_instance(self.storage_engine, self.cls, encoded_values)
        
        # Add to context
        obj_id = encoded_values[ClassInfo.get(self.cls).primary_key_name]
        if self.cls not in self.storage_engine.context:
            self.storage_engine.context[self.cls] = {}
        self.storage_engine.context[self.cls][obj_id] = instance
        
        return instance

transcoder_collection = TranscoderCollection()

@transcoder_collection.add
class BasicsTranscoder(Transcoder):
    supported_types = {
        int: Integer,
        float: Float,
        str: String,
        bool: Boolean
    }

    @classmethod
    def validate(cls, class_info: ClassInfo, field: field) -> bool:
        return field.type in cls.supported_types

    @classmethod
    def setup(cls, setup_args: SetupArgs, field: Field) -> List[Column]:
        column_type = cls.supported_types[field.type]
        return [Column(field.name, column_type, primary_key=setup_args.class_info.is_primary_key(field))]

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Any) -> None:
        merge_args.encodes[merge_args.path.fieldOnParent.name] = value

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Any:
        cf_instance = decode_args.parent._cf_instance
        return cf_instance.encoded_values[decode_args.field.name]

@transcoder_collection.add
class DateTimeTranscoder(Transcoder):
    @classmethod
    def validate(cls, class_info: ClassInfo, field: field) -> bool:
        return field.type == datetime

    @classmethod
    def setup(cls, setup_args: SetupArgs, field: Field) -> List[Column]:
        return [
            Column(f"{field.name}_datetime", DateTime, primary_key=setup_args.class_info.is_primary_key(field)),
            Column(f"{field.name}_timezone", String)
        ]

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: datetime) -> None:
        merge_args.encodes[f"{merge_args.path.fieldOnParent.name}_datetime"] = value.replace(tzinfo=None)
        merge_args.encodes[f"{merge_args.path.fieldOnParent.name}_timezone"] = str(value.tzinfo) if value.tzinfo else None

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> datetime:
        cf_instance = decode_args.parent._cf_instance
        dt = cf_instance.encoded_values[f"{decode_args.field.name}_datetime"]
        tz = cf_instance.encoded_values[f"{decode_args.field.name}_timezone"]
        return dt.replace(tzinfo=tz) if tz else dt

@transcoder_collection.add
class ObjectTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, class_info: ClassInfo, field: field) -> bool:
        return ClassInfo.has_ClassInfo(class_info.cls)

    @classmethod
    def setup(cls, setup_args: SetupArgs, field: Field) -> List[Column]:
        if field is None:
            # This is a top-level object setup
            table_name = f"obj_{setup_args.class_info.cls.__name__}"
            columns = []
            for field_name, field_info in setup_args.class_info.fields.items():
                transcoder = setup_args.class_info.cls.__transcoders__[field_name]
                new_columns = transcoder.setup(setup_args, field_info)
                columns.extend(new_columns)
            Table(table_name, setup_args.storage_engine.metadata, *columns)
            return columns
        else:
            # This is a field setup
            field_class_info = ClassInfo.get(field.type)
            pk_type = field_class_info.fields[field_class_info.primary_key_name].type
            column_type = BasicsTranscoder.supported_types.get(pk_type, String)
            return [Column(f"{field.name}_id", column_type, primary_key=setup_args.class_info.is_primary_key(field))]

    @classmethod
    def _merge(cls, parent_merge_args: SQLMergeArgs, obj: Any) -> None:
        # Create a personal merge_args for this object
        personal_merge_args = SQLMergeArgs(
            context=parent_merge_args.context,
            path=parent_merge_args.path,
            encodes={},
            is_dirty=parent_merge_args.is_dirty,
            storage_engine=parent_merge_args.storage_engine,
            session=parent_merge_args.session
        )
        
        # Get the class info and primary key name
        class_info = ClassInfo.get(type(obj))
        primary_key_name = class_info.primary_key_name
        
        # Check if the object exists in the database
        table = parent_merge_args.storage_engine.metadata.tables[parent_merge_args.storage_engine.get_table_name(type(obj))]
        primary_key = obj.get_primary_key()
        existing_obj = personal_merge_args.session.query(table).filter(getattr(table.c, primary_key_name) == primary_key).first()
        
        is_update = existing_obj is not None
        
        # Iterate through fields and merge
        for field_name, field_info in class_info.fields.items():
            if is_update and field_info.metadata.get('no_update', False):
                continue
            
            value = getattr(obj, field_name)
            transcoder = obj.__class__.__transcoders__[field_name]
            field_merge_args = personal_merge_args.new(field_info)
            transcoder.merge(field_merge_args, value)
        
        # Update the table with our personal encodes
        if is_update:
            personal_merge_args.session.query(table).filter(getattr(table.c, primary_key_name) == primary_key).update(personal_merge_args.encodes)
        else:
            personal_merge_args.session.execute(table.insert().values(**personal_merge_args.encodes))
        
        # Get the primary key
        assert primary_key is not None, f"Primary key for {obj} is None"
        
        # Add object to context
        obj_type = type(obj)
        obj_id = obj.get_primary_key()
        if obj_type not in parent_merge_args.context:
            parent_merge_args.context[obj_type] = {}
        parent_merge_args.context[obj_type][obj_id] = obj
        
    @classmethod
    def _encode(cls, parent_merge_args: SQLMergeArgs, obj: Any) -> None:
        primary_key = obj.get_primary_key()
        
        # Update parent_merge_args.encodes with our primary key
        if parent_merge_args.path.fieldOnParent is None:
            # Top-level object
            parent_merge_args.encodes['id'] = primary_key
        else:
            # Nested object
            parent_merge_args.encodes[f"{parent_merge_args.path.fieldOnParent.name}_id"] = primary_key
        
    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Any:
        cf_instance = decode_args.parent._cf_instance
        field_type = decode_args.field.type
        id_value = cf_instance.encoded_values[f"{decode_args.field.name}_id"]
        return decode_args.storage_engine.query(field_type).filter_by_id(id_value)
    
    @classmethod
    def create_lazy_instance(cls, storage_engine: 'StorageEngine', obj_type: Type, encoded_values: Dict[str, Any]) -> Any:
        instance = object.__new__(obj_type)
        cf_instance = CFInstance(storage_engine)
        cf_instance.encoded_values = encoded_values
        setattr(instance, '_cf_instance', cf_instance)
        
        class_info = ClassInfo.get(obj_type)
        
        for field_name in class_info.fields:
            setattr(instance, field_name, DATADecorator.not_initialized)
        
        for field in class_info.all_fields:
            if field.name not in class_info.fields:
                if field.default is not MISSING:
                    setattr(instance, field.name, field.default)
                elif field.default_factory is not MISSING:
                    setattr(instance, field.name, field.default_factory())
        
        if hasattr(instance, '__post_init__'):
            instance.__post_init__()
        
        return instance