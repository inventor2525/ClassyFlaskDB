from sqlalchemy import Engine, create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session, joinedload
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Table, ForeignKey, Float
from sqlalchemy.orm import registry, relationship, sessionmaker
from sqlalchemy.ext.declarative import declared_attr, DeclarativeMeta

from ClassyFlaskDB.LazyDecorator import LazyDecorator
from ClassyFlaskDB.capture_field_info import capture_field_info, FieldInfo, FieldsInfo
from ClassyFlaskDB.helpers.resolve_type import TypeResolver
from ClassyFlaskDB.to_sql import to_sql

from dataclasses import dataclass, field
from copy import deepcopy

from typing import Any, Dict, List, Type
import uuid

class DATADecorator:
    def __init__(self, *args, **kwargs):
        # Initialize any state or pass any parameters required
        self.args = args
        self.kwargs = kwargs
        self.lazy = LazyDecorator()

    def finalize(self, engine:Engine, globals_return:Dict[str, Any]=globals()) -> registry:
        TypeResolver.append_globals(globals_return)
        self.mapper_registry = registry()
        self.lazy["default"](self.mapper_registry)
        return self.mapper_registry

    def insert_json(self, json_data :dict, session :Session):
        metadata = MetaData()
        metadata.reflect(bind=session.bind)
        
        for table_name, rows in json_data.items():
            table = metadata.tables[table_name]
            for row_data in rows:
                session.execute(table.insert(), row_data)

        session.commit()
        return session
    
    def dump_as_json(self, engine:Engine, session :Session) -> dict:
        metadata = MetaData()
        metadata.reflect(bind=session.bind)
        json_data = {}
        # db_dict = {}
        # with engine.connect() as conn:
        #     for table_name in metadata.tables.keys():
        #         table = metadata.tables[table_name]
        #         rows = conn.execute(table.select()).fetchall()
        #         # Convert each row into a dictionary
        #         # db_dict[table_name] = [dict(row) for row in rows]
        for table_name, table in metadata.tables.items():
            json_data[table_name] = [row._asdict() for row in session.execute(table.select()).fetchall()]

        return json_data
    
    def __call__(self, cls:Type[Any]):
        cls = dataclass(cls)
        cls = capture_field_info(cls)
        if cls.FieldsInfo.primary_key_name is None:
            setattr(cls, "uuid", None)
            cls.__annotations__["uuid"] = str
            init = cls.__init__
            def __init__(self, *args, **kwargs):
                self.uuid = str(uuid.uuid4())
                init(self, *args, **kwargs)
            setattr(cls, "__init__", __init__)
            cls.FieldsInfo.primary_key_name = "uuid"
            if "uuid" not in cls.FieldsInfo.field_names:
                cls.FieldsInfo.field_names.append("uuid")
            if cls.FieldsInfo.type_hints is not None:
                cls.FieldsInfo.type_hints["uuid"] = str
            
        cls = self.lazy([to_sql()])(cls)
    
        # Define a custom __deepcopy__ method
        def __deepcopy__(self, memo):
            if id(self) in memo:
                return memo[id(self)]
            
            cls_copy = self.__class__()
            memo[id(self)] = cls_copy

            for field_name in cls.FieldsInfo.field_names:
                value = getattr(self, field_name, None)
                if value is not None:
                    setattr(cls_copy, field_name, deepcopy(value, memo))
            
            return cls_copy

        # Attach the custom __deepcopy__ method to the class
        setattr(cls, '__deepcopy__', __deepcopy__)
        
        def to_json(cls_self):
            engine = create_engine('sqlite:///:memory:')
            self.mapper_registry.metadata.create_all(engine)

            # Create a session
            Session = sessionmaker(bind=engine)
            session = Session()
            session.merge(deepcopy(cls_self))
            session.commit()

            json_data = self.dump_as_json(engine, session)
            # session.expunge_all()
            session.close()
            engine.dispose()

            return json_data
        @staticmethod
        def from_json(json_data:dict):
            engine = create_engine('sqlite:///:memory:')
            self.mapper_registry.metadata.create_all(engine)

            # Create a session
            Session = sessionmaker(bind=engine)
            session = Session()

            session = self.insert_json(json_data, session)
            objs = deepcopy( session.query(cls).options(joinedload('*')).all() )
            # session.expunge_all()
            session.close()
            engine.dispose()
            return objs
        setattr(cls, "to_json", to_json)
        setattr(cls, "from_json", from_json)
        return cls

DATA = DATADecorator()