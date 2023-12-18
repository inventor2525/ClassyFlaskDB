from sqlalchemy import Engine, create_engine, MetaData, DateTime
from sqlalchemy.orm import sessionmaker, Session, joinedload
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Table, ForeignKey, Float
from sqlalchemy.orm import registry, relationship, sessionmaker
from sqlalchemy.ext.declarative import declared_attr, DeclarativeMeta

from ClassyFlaskDB.Decorators.LazyDecorator import LazyDecorator
from ClassyFlaskDB.Decorators.capture_field_info import capture_field_info, FieldInfo, FieldsInfo
from ClassyFlaskDB.helpers.resolve_type import TypeResolver
from ClassyFlaskDB.Decorators.to_sql import to_sql

from dataclasses import dataclass, field
from copy import deepcopy

from typing import Any, Dict, List, Type
import uuid
from sqlalchemy.orm import class_mapper
import sqlalchemy
from datetime import datetime
from enum import Enum
from ClassyFlaskDB.Decorators.AnyParam import AnyParam
from contextlib import contextmanager

def convert_to_column_type(value, column_type):
    if isinstance(column_type, DateTime):
        try:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f %z")
        except ValueError:
            # Try parsing without timezone
            return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S.%f")
    return value

class ID_Type(Enum):
    UUID = "uuid"
    HASHID = "hashid"

class DATAEngine:
    def __init__(self, data_decorator:"DATADecorator", engine:Engine=None, engine_str:str="sqlite:///:memory:"):
        self.data_decorator = data_decorator
        self.data_decorator.finalize()
        
        if engine is None:
            self.engine = create_engine(engine_str)
        else:
            self.engine = engine
        
        self.data_decorator.mapper_registry.metadata.create_all(self.engine)
        self.session_maker = sessionmaker(bind=self.engine)
    
    def add(self, obj:Any):
        obj = deepcopy(obj)
        with self.session_maker() as session:
            session.add(obj)
            session.commit()
    
    def merge(self, obj:Any):
        obj = deepcopy(obj)
        with self.session_maker() as session:
            session.merge(obj)
            session.commit()
    
    @contextmanager
    def session(self):
        session = self.session_maker()
        try:
            yield session
        except:
            session.rollback()
            raise
        finally:
            session.close()
    
    def to_json(self) -> dict:
        with self.session_maker() as session:
            metadata = MetaData()
            metadata.reflect(bind=session.bind)
            json_data = {}
            
            for table_name, table in metadata.tables.items():
                json_data[table_name] = [row._asdict() for row in session.execute(table.select()).fetchall()]

            return json_data
    
    def insert_json(self, json_data :dict) -> None:
        with self.session_maker() as session:
            metadata = MetaData()
            metadata.reflect(bind=session.bind)
            
            for table_name, rows in json_data.items():
                table = metadata.tables[table_name]

                # Identify columns that require conversion
                columns_to_convert = {
                    column_name: column.type
                    for column_name, column in table.columns.items()
                    if isinstance(column.type, DateTime)
                }

                # Prepare and insert data for each row
                for row_data in rows:
                    if columns_to_convert:
                        # Only copy and convert if necessary
                        row_copy = row_data.copy()
                        for column_name, column_type in columns_to_convert.items():
                            if column_name in row_copy:
                                row_copy[column_name] = convert_to_column_type(row_copy[column_name], column_type)
                        session.execute(table.insert(), row_copy)
                    else:
                        # Insert directly if no conversions are needed
                        session.execute(table.insert(), row_data)

            session.commit()
    
    def dispose(self):
        self.engine.dispose()

class DATADecorator(AnyParam):
    def __init__(self, *args, **kwargs):
        # Initialize any state or pass any parameters required
        self.args = args
        self.kwargs = kwargs
        self.lazy = LazyDecorator()
        self.decorated_classes = {}
        
        self._finalized = False
    
    def finalize(self, globals_return:Dict[str, Any]=globals()) -> None:
        if self._finalized:
            return
            
        TypeResolver.append_globals(globals_return)
        TypeResolver.append_globals(self.decorated_classes)
        self.mapper_registry = registry()
        self.lazy["default"](self.mapper_registry)
        self._finalized = True
    
    def decorate(self, cls:Type[Any], generated_id_type:ID_Type=ID_Type.UUID, hashed_fields:List[str]=None) -> Type[Any]:
        lazy_decorators = []
        self.decorated_classes[cls.__name__] = cls

        cls = dataclass(cls)
        cls = capture_field_info(cls)
        if cls.FieldsInfo.primary_key_name is None:
            def add_pk(pk_name:str, pk_type:Type):
                setattr(cls, pk_name, None)
                cls.__annotations__[pk_name] = pk_type
                
                cls.FieldsInfo.primary_key_name = pk_name
                if pk_name not in cls.FieldsInfo.field_names:
                    cls.FieldsInfo.field_names.append(pk_name)
                    
                if cls.FieldsInfo.type_hints is not None:
                    cls.FieldsInfo.type_hints[pk_name] = pk_type
            
            if generated_id_type == ID_Type.UUID:
                def new_id(self):
                    self.uuid = str(uuid.uuid4())
                setattr(cls, "new_id", new_id)
                add_pk("uuid", str)
                
            elif generated_id_type == ID_Type.HASHID:
                import hashlib
                
                if hashed_fields is None:
                    hashed_fields = deepcopy(cls.FieldsInfo.field_names)
                
                def get_hash_field_getters(cls: Type) -> Type:
                    field_getters = {}
                    for field_name in hashed_fields:
                        hashed_field_type = cls.FieldsInfo.get_field_type(field_name)
                        
                        if getattr(hashed_field_type, "FieldsInfo", None) is not None:
                            def field_getter(self, field_name:str):
                                obj = getattr(self, field_name)
                                if obj is None:
                                    return ""
                                return str(obj.get_primary_key())
                            field_getters[field_name] = field_getter
                        elif hasattr(hashed_field_type, "__origin__") and hashed_field_type.__origin__ in [list, tuple]:
                            list_type = hashed_field_type.__args__[0]
                            if getattr(list_type, "FieldsInfo", None) is not None:
                                def field_getter(self, field_name:str):
                                    l = getattr(self, field_name)
                                    if l is None:
                                        return "[]"
                                    l_str = ",".join([str(None if item is None else item.get_primary_key()) for item in l])
                                    return f"[{l_str}]"
                                field_getters[field_name] = field_getter
                            else:
                                def field_getter(self, field_name:str):
                                    return str(getattr(self, field_name))
                                field_getters[field_name] = field_getter
                        else:
                            def field_getter(self, field_name:str):
                                return str(getattr(self, field_name))
                            field_getters[field_name] = field_getter
                    cls.__field_getters__ = field_getters
                    return cls
                    
                lazy_decorators.append(get_hash_field_getters)
                
                def new_id(self) -> str:
                    fields = [cls.__field_getters__[field_name](self,field_name) for field_name in hashed_fields]
                    self.hashid = hashlib.sha256(",".join(fields).encode("utf-8")).hexdigest()
                setattr(cls, "new_id", new_id)
                add_pk("hashid", str)
            
            init = cls.__init__
            def __init__(self, *args, **kwargs):
                init(self, *args, **kwargs)
                self.new_id()
            setattr(cls, "__init__", __init__)
                
        def get_primary_key(self):
            return getattr(self, cls.FieldsInfo.primary_key_name)
        setattr(cls, "get_primary_key", get_primary_key)
        
        cls = self.lazy([to_sql(), *lazy_decorators])(cls)
    
        # Define a custom __deepcopy__ method
        def __deepcopy__(self, memo):
            if id(self) in memo:
                return memo[id(self)]
            
            mapper = class_mapper(self.__class__)
            cls_copy = mapper.class_manager.new_instance()
            # cls_copy = self.__class__()
            memo[id(self)] = cls_copy
            
            def fields(cls):
                for field_name in cls.FieldsInfo.field_names:
                    yield field_name
                if hasattr(cls, "__cls_type__"):
                    yield "__cls_type__"

            for field_name in fields(cls):
                value = getattr(self, field_name, None)
                if value is not None:
                    if isinstance(value, sqlalchemy.orm.collections.InstrumentedList):
                        setattr(cls_copy, field_name, deepcopy(list(value), memo))
                    # elif isinstance(value, dict):
                    #     setattr(cls_copy, field_name, deepcopy(value, memo))
                    else:
                        setattr(cls_copy, field_name, deepcopy(value, memo))
            
            return cls_copy

        # Attach the custom __deepcopy__ method to the class
        setattr(cls, '__deepcopy__', __deepcopy__)
        
        def to_json(cls_self):
            engine = DATAEngine(self)
            
            obj = deepcopy(cls_self)
            
            engine.merge(obj)

            json_data = engine.to_json()
            engine.dispose()
            
            return {
                "primary_key":obj.get_primary_key(),
                "type":type(obj).__name__,
                "obj":json_data
            }
            
        @staticmethod
        def from_json(json_data:dict):
            engine = DATAEngine(self)
            engine.insert_json(json_data["obj"])
            
            pk_col = cls.__table__.c[cls.FieldsInfo.primary_key_name]
            with engine.session() as session:
                objs = deepcopy( session.query(cls).options(joinedload('*')).filter(pk_col==json_data["primary_key"]).first() )
                
            engine.dispose()
            return objs
            
        setattr(cls, "to_json", to_json)
        setattr(cls, "from_json", from_json)
        return cls

DATA = DATADecorator()