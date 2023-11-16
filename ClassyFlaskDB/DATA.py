from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker
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

    def finalize(self, engine:Engine):
        mapper_registry = registry()
        self.lazy["default"](mapper_registry)
        mapper_registry.metadata.create_all(engine)

    def __call__(self, cls:Type[Any]):
        cls = dataclass(cls)
        cls = capture_field_info(cls)
        cls = self.lazy([to_sql()])(cls)
        return cls

DATA = DATADecorator()