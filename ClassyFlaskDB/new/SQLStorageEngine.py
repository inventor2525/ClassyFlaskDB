from sqlalchemy import create_engine, Table, Column, Integer, String, Float, DateTime, Boolean, select, MetaData
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, Type, List, Generic, TypeVar, Iterator, Optional, get_origin, get_args
from dataclasses import dataclass, field, Field, MISSING
from datetime import datetime
import uuid

from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.StorageEngine import StorageEngine, TranscoderCollection
from ClassyFlaskDB.new.Transcoder import Transcoder, LazyLoadingTranscoder
from ClassyFlaskDB.new.Args import MergeArgs, SetupArgs, DecodeArgs, CFInstance
from ClassyFlaskDB.new.ClassInfo import ClassInfo
from ClassyFlaskDB.new.Types import Interface, BasicType, ContextType
from ClassyFlaskDB.new.InstrumentedList import InstrumentedList, ListCFInstance
from ClassyFlaskDB.new.InstrumentedDict import InstrumentedDict, DictCFInstance

from sqlalchemy.orm import Session

@dataclass
class SQLMergeArgs(MergeArgs):
    session: Session

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
            transcoder = self.get_transcoder_type(cls)
            transcoder.setup(setup_args, None, cls, False)

        self.metadata.create_all(self.engine)

    def merge(self, obj: Any, persist: bool = False):
        context = self.context if persist else {}
        with self.session_maker() as session:
            merge_args = SQLMergeArgs(
                storage_engine=self,
                context=context,
                is_dirty={},
                encodes={},
                base_name='id',
                type=type(obj),
                session=session
            )
            transcoder = self.get_transcoder_type(type(obj))
            transcoder.merge(merge_args, obj)
            session.commit()

    def get_table_name(self, cls: Type) -> str:
        return f"obj_{cls.__name__}"

    def get_transcoder_type(self, type_: Type) -> Type[Transcoder]:
        for transcoder in self.transcoders:
            try:
                if transcoder.validate(type_):
                    return transcoder
            except:
                pass
        raise ValueError(f"No suitable transcoder found for {type_}")
    
    def query(self, cls: Type[T]) -> 'SQLAlchemyStorageEngineQuery[T]':
        return SQLAlchemyStorageEngineQuery(self, cls)
    
    def get_table_by_name(self, table_name: str) -> Table:
        if table_name in self.metadata.tables:
            return self.metadata.tables[table_name]
        else:
            raise ValueError(f"Table '{table_name}' not found in metadata")

T = TypeVar('T')
class SQLAlchemyStorageEngineQuery(Generic[T]):
    def __init__(self, storage_engine: SQLAlchemyStorageEngine, cls: Type[T]):
        self.storage_engine = storage_engine
        self.cls = cls
        self.table = storage_engine.metadata.tables[storage_engine.get_table_name(cls)]
        self.query = select(self.table)
        self.transcoder:LazyLoadingTranscoder = storage_engine.get_transcoder_type(cls)
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
        instance = self.transcoder.create_lazy_instance(cf_instance = CFInstance(
            decode_args=DecodeArgs(
                storage_engine=self.storage_engine,
                encodes=encoded_values,
                base_name=None,
                type=self.cls
            )
        ))
        
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
    def validate(cls, type_: Type) -> bool:
        return type_ in cls.supported_types

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Column]:
        column_type = cls.supported_types[type_]
        return [Column(name, column_type, primary_key=is_primary_key)]
    
    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Any) -> None:
        merge_args.encodes[merge_args.base_name] = value

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Any:
        value = decode_args.encodes[decode_args.base_name]
        return decode_args.type(value)

@transcoder_collection.add
class DateTimeTranscoder(Transcoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return type_ == datetime

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Column]:
        return [
            Column(f"{name}_datetime", DateTime, primary_key=is_primary_key),
            Column(f"{name}_timezone", String)
        ]

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: datetime) -> None:
        merge_args.encodes[f"{merge_args.base_name}_datetime"] = value.replace(tzinfo=None)
        merge_args.encodes[f"{merge_args.base_name}_timezone"] = str(value.tzinfo) if value.tzinfo else None

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> datetime:
        dt = decode_args.encodes[f"{decode_args.base_name}_datetime"]
        tz = decode_args.encodes[f"{decode_args.base_name}_timezone"]
        return dt.replace(tzinfo=tz) if tz else dt

@transcoder_collection.add
class ObjectTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return ClassInfo.has_ClassInfo(type_)

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Column]:
        if name is None:
            # This is a top-level object setup
            table_name = f"obj_{setup_args.class_info.cls.__name__}"
            columns = []
            for field_name, field_info in setup_args.class_info.fields.items():
                transcoder = setup_args.class_info.cls.__transcoders__[field_name]
                new_columns = transcoder.setup(setup_args, field_name, field_info.type, setup_args.class_info.is_primary_key(field_info))
                columns.extend(new_columns)
            Table(table_name, setup_args.storage_engine.metadata, *columns, extend_existing=True)
            return columns
        else:
            # This is a field setup
            field_class_info = ClassInfo.get(type_)
            pk_type = field_class_info.fields[field_class_info.primary_key_name].type
            column_type = BasicsTranscoder.supported_types.get(pk_type, String)
            return [
                Column(f"{name}_id", column_type, primary_key=is_primary_key),
                Column(f"{name}_type", String)
            ]

    @classmethod
    def _merge(cls, parent_merge_args: SQLMergeArgs, obj: DATADecorator.Interface) -> None:
        # Create a personal merge_args for this object
        personal_merge_args = parent_merge_args.new(encodes={})
        
        # Get the class info and primary key name
        class_info = ClassInfo.get(type(obj))
        primary_key_name = class_info.primary_key_name
        
        # Check if the object exists in the database
        table = parent_merge_args.storage_engine.metadata.tables[parent_merge_args.storage_engine.get_table_name(type(obj))]
        primary_key = obj.get_primary_key()
        existing_obj = personal_merge_args.session.query(table).filter(getattr(table.c, primary_key_name) == primary_key).first()
        
        is_update = existing_obj is not None
        
        # Iterate through fields and merge
        for field in class_info.fields.values():
            if is_update and field.metadata.get('no_update', False):
                continue
            
            value = getattr(obj, field.name)
            transcoder = obj.__transcoders__[field.name]
            field_merge_args = personal_merge_args.new(
                base_name = field.name,
                type = field.type
            )
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
        parent_merge_args.storage_engine.context.get(obj_type, {}).pop(obj_id, None)
        if obj_type not in parent_merge_args.context:
            parent_merge_args.context[obj_type] = {}
        parent_merge_args.context[obj_type][obj_id] = obj
        
    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Any) -> None:
        value_type = type(value)
        assert issubclass(value_type, merge_args.type), f"Type hint not obeyed. This is what we know {merge_args}"
        class_info = ClassInfo.get(value_type)
        primary_key = getattr(value, class_info.primary_key_name)
        merge_args.encodes[f"{merge_args.base_name}_id"] = primary_key
        merge_args.encodes[f"{merge_args.base_name}_type"] = class_info.semi_qualname
        
    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Any:
        id_value = decode_args.encodes[f"{decode_args.base_name}_id"]
        type_name = decode_args.encodes[f"{decode_args.base_name}_type"]
        obj_type = decode_args.storage_engine.data_decorator.registry[type_name]
        return decode_args.storage_engine.query(obj_type).filter_by_id(id_value)
    
    @classmethod
    def create_lazy_instance(cls, cf_instance: CFInstance) -> Any:
        instance = object.__new__(cf_instance.decode_args.type)
        
        setattr(instance, '_cf_instance', cf_instance)
        
        class_info = ClassInfo.get(cf_instance.decode_args.type)
        
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

from enum import Enum

@transcoder_collection.add
class EnumTranscoder(Transcoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return issubclass(type_, Enum)

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Column]:
        return [Column(name, String, primary_key=is_primary_key)]

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Enum) -> None:
        merge_args.encodes[merge_args.base_name] = value.name

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Enum:
        enum_value = decode_args.encodes[decode_args.base_name]
        return decode_args.type[enum_value]
    
@transcoder_collection.add
class ListTranscoder(LazyLoadingTranscoder):
    list_id_mapping: Dict[int, str] = {}

    @classmethod
    def validate(cls, type_: Type) -> bool:
        return get_origin(type_) is list

    @classmethod
    def get_table_name(cls, value_type: Type) -> str:
        origin = get_origin(value_type)
        return f"list_{origin.__name__ if origin else value_type.__name__}"

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Column]:
        value_type = get_args(type_)[0]
        table_name = cls.get_table_name(value_type)
        value_transcoder = setup_args.storage_engine.get_transcoder_type(value_type)
        
        columns = [
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('list_id', String),
            Column('index', Integer)
        ]
        
        value_columns = value_transcoder.setup(setup_args, "value", value_type, False)
        columns.extend(value_columns)
        
        # Add extend_existing=True to handle cases where the table might already exist
        Table(table_name, setup_args.storage_engine.metadata, *columns, extend_existing=True)
        return [Column(f"{name}_id", String, primary_key=is_primary_key)]

    @classmethod
    def _merge(cls, merge_args: SQLMergeArgs, value: List[Any]) -> None:
        value_type = get_args(merge_args.type)[0]
        value_transcoder = merge_args.storage_engine.get_transcoder_type(value_type)
        
        table_name = cls.get_table_name(value_type)
        table = merge_args.storage_engine.get_table_by_name(table_name)
        
        list_id = cls._get_or_create_list_id(value)
        
        # Clear existing entries
        merge_args.session.query(table).filter(table.c.list_id == list_id).delete()
        
        for index, item in enumerate(value):
            item_merge_args = merge_args.new(
                encodes={},
                base_name='value',
                type=value_type
            )
            value_transcoder.merge(item_merge_args, item)
            
            row = {
                'list_id': list_id,
                'index': index,
                **item_merge_args.encodes
            }
            merge_args.session.execute(table.insert().values(**row))

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: List[Any]) -> None:
        list_id = cls._get_or_create_list_id(value)
        merge_args.encodes[f"{merge_args.base_name}_id"] = list_id

    @classmethod
    def _get_or_create_list_id(cls, value: List[Any]) -> str:
        if isinstance(value, InstrumentedList):
            return value._cf_instance.list_id
        list_id = cls.list_id_mapping.get(id(value), MISSING)
        if list_id is MISSING:
            list_id = str(uuid.uuid4())
            cls.list_id_mapping[id(value)] = list_id
        return list_id

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> InstrumentedList:
        value_type = get_args(decode_args.type)[0]
        value_transcoder = decode_args.storage_engine.get_transcoder_type(value_type)
        
        table_name = cls.get_table_name(value_type)
        table = decode_args.storage_engine.get_table_by_name(table_name)
        
        list_id = decode_args.encodes[f"{decode_args.base_name}_id"]
        
        with decode_args.storage_engine.session_maker() as session:
            query = session.query(table).filter(table.c.list_id == list_id).order_by(table.c.index)
            encoded_values = [row._asdict() for row in query.all()]
        
        return cls.create_lazy_instance(ListCFInstance(
            decode_args=decode_args.new(
                encodes = encoded_values
            ),
            list_id = list_id,
            value_type = value_type,
            value_transcoder = value_transcoder
        ))

    @classmethod
    def create_lazy_instance(cls, cf_instance:DictCFInstance) -> InstrumentedDict:
        lazy_list = InstrumentedList()
        lazy_list._cf_instance = cf_instance
        # Pre-populate the list with placeholder objects
        lazy_list.extend([MISSING for _ in range(len(cf_instance.decode_args.encodes))])
        return lazy_list

@transcoder_collection.add
class DictionaryTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return get_origin(type_) is dict

    @classmethod
    def get_table_name(cls, key_type: Type, value_type: Type) -> str:
        return f"dict_{key_type.__name__}_{value_type.__name__}"

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Column]:
        key_type, value_type = get_args(type_)
        table_name = cls.get_table_name(key_type, value_type)
        key_transcoder = setup_args.storage_engine.get_transcoder_type(key_type)
        value_transcoder = setup_args.storage_engine.get_transcoder_type(value_type)
        
        columns = [
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('dict_id', String),
        ]
        
        key_columns = key_transcoder.setup(setup_args, "key", key_type, False)
        value_columns = value_transcoder.setup(setup_args, "value", value_type, False)
        columns.extend(key_columns)
        columns.extend(value_columns)
        
        Table(table_name, setup_args.storage_engine.metadata, *columns, extend_existing=True)
        return [Column(f"{name}_id", String, primary_key=is_primary_key)]

    @classmethod
    def _merge(cls, merge_args: SQLMergeArgs, value: dict) -> None:
        key_type, value_type = get_args(merge_args.type)
        key_transcoder = merge_args.storage_engine.get_transcoder_type(key_type)
        value_transcoder = merge_args.storage_engine.get_transcoder_type(value_type)
        
        table_name = cls.get_table_name(key_type, value_type)
        table = merge_args.storage_engine.get_table_by_name(table_name)
        
        dict_id = cls._get_or_create_dict_id(value)
        
        merge_args.session.query(table).filter(table.c.dict_id == dict_id).delete()
        
        for key, item in value.items():
            key_merge_args = merge_args.new(encodes={}, base_name='key', type=key_type)
            value_merge_args = merge_args.new(encodes={}, base_name='value', type=value_type)
            
            key_transcoder.merge(key_merge_args, key)
            value_transcoder.merge(value_merge_args, item)
            
            row = {
                'dict_id': dict_id,
                **key_merge_args.encodes,
                **value_merge_args.encodes
            }
            merge_args.session.execute(table.insert().values(**row))

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: dict) -> None:
        dict_id = cls._get_or_create_dict_id(value)
        merge_args.encodes[f"{merge_args.base_name}_id"] = dict_id

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> InstrumentedDict:
        key_type, value_type = get_args(decode_args.type)
        key_transcoder = decode_args.storage_engine.get_transcoder_type(key_type)
        value_transcoder = decode_args.storage_engine.get_transcoder_type(value_type)
        
        table_name = cls.get_table_name(key_type, value_type)
        table = decode_args.storage_engine.get_table_by_name(table_name)
        
        dict_id = decode_args.encodes[f"{decode_args.base_name}_id"]
        
        with decode_args.storage_engine.session_maker() as session:
            query = session.query(table).filter(table.c.dict_id == dict_id)
            encoded_values = [row._asdict() for row in query.all()]
        
        return cls.create_lazy_instance(DictCFInstance(
            decode_args=decode_args.new(encodes=encoded_values),
            dict_id=dict_id,
            key_type=key_type,
            value_type=value_type,
            key_transcoder=key_transcoder,
            value_transcoder=value_transcoder
        ))

    @classmethod
    def create_lazy_instance(cls, cf_instance:DictCFInstance) -> InstrumentedDict:
        lazy_dict = InstrumentedDict()
        lazy_dict._cf_instance = cf_instance
        return lazy_dict

    @classmethod
    def _get_or_create_dict_id(cls, value: dict) -> str:
        if isinstance(value, InstrumentedDict):
            return value._cf_instance.dict_id
        dict_id = cls.dict_id_mapping.get(id(value), MISSING)
        if dict_id is MISSING:
            dict_id = str(uuid.uuid4())
            cls.dict_id_mapping[id(value)] = dict_id
        return dict_id

    dict_id_mapping: Dict[int, str] = {}