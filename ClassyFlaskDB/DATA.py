from sqlalchemy import Engine, create_engine, MetaData
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Table, ForeignKey, Float
from sqlalchemy.orm import registry, relationship, sessionmaker
from sqlalchemy.ext.declarative import declared_attr, DeclarativeMeta
from sqlalchemy import inspect

from ClassyFlaskDB.LazyDecorator import LazyDecorator
from ClassyFlaskDB.capture_field_info import capture_field_info, FieldInfo, FieldsInfo
from ClassyFlaskDB.to_sql import to_sql

from dataclasses import dataclass, field

from typing import Any, List, Type

class DATADecorator:
    def __init__(self, *args, **kwargs):
        # Initialize any state or pass any parameters required
        self.args = args
        self.kwargs = kwargs
        self.lazy = LazyDecorator()

    def finalize(self, engine:Engine) -> registry:
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
        cls = self.lazy([to_sql()])(cls)

        def to_json(cls_self):
            engine = create_engine('sqlite:///:memory:')
            self.mapper_registry.metadata.create_all(engine)

            # Create a session
            Session = sessionmaker(bind=engine)
            session = Session()
            from copy import deepcopy
            session.add_all([deepcopy(cls_self)])
            session.commit()

            json_data = self.dump_as_json(engine, session)
            return json_data
        @staticmethod
        def from_json(json_data:dict):
            engine = create_engine('sqlite:///:memory:')
            self.mapper_registry.metadata.create_all(engine)

            # Create a session
            Session = sessionmaker(bind=engine)
            session = Session()

            session = self.insert_json(json_data, session)
            return session.query(cls).all()
        setattr(cls, "to_json", to_json)
        setattr(cls, "from_json", from_json)
        return cls

DATA = DATADecorator()