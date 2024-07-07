from sqlalchemy import create_engine, Table, Column, Integer, String, Float, DateTime, Boolean, select, MetaData
from sqlalchemy.orm import sessionmaker
from typing import Dict, Any, Type, List, Generic, TypeVar
from dataclasses import dataclass, field
from datetime import datetime

from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.StorageEngine import StorageEngine
from ClassyFlaskDB.new.Transcoder import Transcoder
from ClassyFlaskDB.new.Args import MergeArgs, MergePath
from ClassyFlaskDB.new.ClassInfo import ClassInfo
from ClassyFlaskDB.new.Types import Interface, BasicType, ContextType

class CFInstance:
    def __init__(self):
        self.storage_engine = None
        self.loaded_fields = set()
        self.encoded_values = {}

class TranscoderCollection:
    def __init__(self):
        self.transcoders = []

    def add(self, transcoder_cls):
        self.transcoders.append(transcoder_cls)
        return transcoder_cls

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
            table_name = self.get_table_name(cls)
            columns = []
            primary_key_name = class_info.primary_key_name
            cls.__transcoders__ = {}
            for field_name, field_info in class_info.fields.items():
                transcoder = self.get_transcoder_type(class_info, field_info)
                cls.__transcoders__[field_name] = transcoder()
                new_columns = transcoder.setup(class_info, field_info, field_name == primary_key_name)
                columns.extend(new_columns)
            Table(table_name, self.metadata, *columns)
        self.metadata.create_all(self.engine)

    def merge(self, obj: Any):
        with self.session_maker() as session:
            merge_args = MergeArgs(
                context={},
                path=MergePath(parentObj=None, fieldOnParent=None),
                encodes={},
                is_dirty={},
                storage_engine=self
            )
            transcoder = self.get_transcoder_type(ClassInfo.get(type(obj)), None)
            transcoder.merge(merge_args, obj)
            
            print(f"Final merge_args.encodes: {merge_args.encodes}")
            
            # table = self.metadata.tables[self.get_table_name(type(obj))]
            # session.execute(table.insert().values(**merge_args.encodes))
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

    def filter_by_id(self, id_value: Any) -> T:
        class_info = ClassInfo.get(self.cls)
        primary_key_name = class_info.primary_key_name
        self.query = self.query.where(getattr(self.table.c, primary_key_name) == id_value)
        result = self._execute_query_first()
        print(f"Query result for {self.cls.__name__} with ID {id_value}: {result}")
        return result

    def all(self) -> List[T]:
        return self._execute_query_all()

    def _execute_query_first(self) -> T:
        with self.storage_engine.session_maker() as session:
            result = session.execute(self.query).first()
            return self._create_lazy_instance(result) if result else None

    def _execute_query_all(self) -> List[T]:
        with self.storage_engine.session_maker() as session:
            results = session.execute(self.query).fetchall()
            return [self._create_lazy_instance(row) for row in results]

    def _create_lazy_instance(self, row):
        instance = object.__new__(self.cls)
        cf_instance = CFInstance(self.storage_engine)
        
        class_info = ClassInfo.get(self.cls)
        for field_name, field_info in class_info.fields.items():
            transcoder = self.cls.__transcoders__[field_name]
            columns = transcoder.get_columns(class_info, field_info)
            cf_instance.encoded_values[field_name] = {col: row[col] for col in columns if col in row.keys()}
        
        object.__setattr__(instance, '_cf_instance', cf_instance)
        
        # Call __init__ with default values to ensure the object is properly initialized
        init_args = [row.get(field, None) for field in class_info.fields]
        instance.__init__(*init_args)
        
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
    def setup(cls, class_info: ClassInfo, field: field, is_primary_key: bool) -> List[Column]:
        column_type = cls.supported_types[field.type]
        return [Column(field.name, column_type, primary_key=is_primary_key)]

    @classmethod
    def _merge(cls, merge_args: MergeArgs, value: Any) -> None:
        merge_args.encodes[merge_args.path.fieldOnParent.name] = value
        print(f"Basic merge for {merge_args.path.fieldOnParent.name}: {merge_args.encodes}")

    @classmethod
    def get_columns(cls, class_info: ClassInfo, field: field) -> List[str]:
        return [field.name]

    @classmethod
    def decode(cls, storage_engine: SQLAlchemyStorageEngine, obj: Any, field_name: str, encoded_values: Dict[str, Any]) -> Any:
        return encoded_values[field_name]

@transcoder_collection.add
class DateTimeTranscoder(Transcoder):
    @classmethod
    def validate(cls, class_info: ClassInfo, field: field) -> bool:
        return field.type == datetime

    @classmethod
    def setup(cls, class_info: ClassInfo, field: field, is_primary_key: bool) -> List[Column]:
        return [
            Column(f"{field.name}_datetime", DateTime, primary_key=is_primary_key),
            Column(f"{field.name}_timezone", String)
        ]

    @classmethod
    def _merge(cls, merge_args: MergeArgs, value: datetime) -> None:
        merge_args.encodes[f"{merge_args.path.fieldOnParent.name}_datetime"] = value.replace(tzinfo=None)
        merge_args.encodes[f"{merge_args.path.fieldOnParent.name}_timezone"] = str(value.tzinfo) if value.tzinfo else None

    @classmethod
    def get_columns(cls, class_info: ClassInfo, field: field) -> List[str]:
        return [f"{field.name}_datetime", f"{field.name}_timezone"]

    @classmethod
    def decode(cls, storage_engine: SQLAlchemyStorageEngine, obj: Any, field_name: str, encoded_values: Dict[str, Any]) -> datetime:
        dt = encoded_values[f"{field_name}_datetime"]
        tz = encoded_values[f"{field_name}_timezone"]
        return dt.replace(tzinfo=tz) if tz else dt

@transcoder_collection.add
class ObjectTranscoder(Transcoder):
    @classmethod
    def validate(cls, class_info: ClassInfo, field: field) -> bool:
        return ClassInfo.has_ClassInfo(class_info.cls)

    @classmethod
    def setup(cls, class_info: ClassInfo, field: field, is_primary_key: bool) -> List[Column]:
        field_class_info = ClassInfo.get(field.type)
        pk_type = field_class_info.fields[field_class_info.primary_key_name].type
        column_type = BasicsTranscoder.supported_types.get(pk_type, String)
        return [Column(f"{field.name}_id", column_type, primary_key=is_primary_key)]

    @classmethod
    def _merge(cls, parent_merge_args: MergeArgs, obj: Any) -> None:
        print(f"Merging object: {obj}")
        
        # Create a personal merge_args for this object
        personal_merge_args = MergeArgs(
            context=parent_merge_args.context,
            path=parent_merge_args.path,
            encodes={},
            is_dirty=parent_merge_args.is_dirty,
            storage_engine=parent_merge_args.storage_engine
        )
        
        # Iterate through fields and merge
        for field_name, field_info in obj.__class_info__.fields.items():
            value = getattr(obj, field_name)
            transcoder = obj.__class__.__transcoders__[field_name]
            field_merge_args = personal_merge_args.new(field_info)
            transcoder.merge(field_merge_args, value)
        
        # Get the table for this object
        table = parent_merge_args.storage_engine.metadata.tables[parent_merge_args.storage_engine.get_table_name(type(obj))]
        
        # Update the table with our personal encodes
        with parent_merge_args.storage_engine.session_maker() as session:
            session.execute(table.insert().values(**personal_merge_args.encodes))
            session.commit()
        
        # Get the primary key
        primary_key = obj.get_primary_key()
        assert primary_key is not None, f"Primary key for {obj} is None"
        
        # Update parent_merge_args.encodes with our primary key
        if parent_merge_args.path.fieldOnParent is None:
            # Top-level object
            parent_merge_args.encodes['id'] = primary_key
        else:
            # Nested object
            parent_merge_args.encodes[f'{parent_merge_args.path.fieldOnParent.name}_id'] = primary_key
        
        print(f"Final personal encodes: {personal_merge_args.encodes}")
        print(f"Updated parent encodes: {parent_merge_args.encodes}")
            
    @classmethod
    def get_columns(cls, class_info: ClassInfo, field: field) -> List[str]:
        return [f"{field.name}_id"]

    @classmethod
    def decode(cls, storage_engine: SQLAlchemyStorageEngine, obj: Any, field_name: str, encoded_values: Dict[str, Any]) -> Any:
        field_type = obj.__class_info__.fields[field_name].type
        id_value = encoded_values[f"{field_name}_id"]
        return storage_engine.query(field_type).filter_by_id(id_value)

# Example usage
DATA = DATADecorator()

@DATA
@dataclass
class Person:
    name: str
    age: int
    height: float
    birth_date: datetime

@DATA
@dataclass
class ImmediateFamily:
    surname: str
    child: Person
    mother: Person
    father: Person

# Initialize the storage engine
engine = SQLAlchemyStorageEngine("sqlite:///:memory:", transcoder_collection, DATA)

# Create test instances
child = Person("Alice", 10, 140.0, datetime(2013, 5, 15))
mother = Person("Eve", 35, 165.5, datetime(1988, 9, 22))
father = Person("Bob", 37, 180.0, datetime(1986, 3, 10))
family = ImmediateFamily("Smith", child, mother, father)

# Merge the family object
engine.merge(family)

# Query and demonstrate lazy loading
queried_family = engine.query(ImmediateFamily).filter_by_id(family.get_primary_key())
print(queried_family.surname)  # This will not trigger lazy loading
print(queried_family.child.name)  # This will trigger lazy loading for the child object and its name
print(queried_family.mother.birth_date)  # This will trigger lazy loading for the mother object and its birth date