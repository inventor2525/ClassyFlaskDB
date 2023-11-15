from ClassyFlaskDB.to_sql import to_sql

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Table, ForeignKey, Float
from sqlalchemy.orm import registry, relationship, sessionmaker
from sqlalchemy.ext.declarative import declared_attr, DeclarativeMeta
from sqlalchemy import inspect
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from ClassyFlaskDB.LazyDecorator import LazyDecorator
from ClassyFlaskDB.capture_field_info import capture_field_info, FieldInfo, FieldsInfo

from dataclasses import dataclass, field

from typing import List
lazzy = LazyDecorator()

# Define an engine and base
engine = create_engine('sqlite:///:memory:')
mapper_registry = registry()
Base = declarative_base()

@lazzy([to_sql()])
@capture_field_info
@dataclass
class Bar:
    id: str

@lazzy([to_sql()])
@capture_field_info
@dataclass
class Foo:
    id: int
    bar: Bar
    bars: List[Bar] = field(default_factory=list)

lazzy["default"](mapper_registry)
mapper_registry.metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Example usage
bar_instance = Bar(id='bar1')
foo_instance = Foo(id=1, bar=bar_instance)
foo_instance.bars.append(Bar(id='bar2'))
foo_instance.bars.append(Bar(id='bar3'))

# Add to the session and commit
session.add_all([foo_instance, bar_instance])
session.commit()

# Query
queried_foo = session.query(Foo).filter_by(id=1).first()

if queried_foo and queried_foo.bar:
    print(f"Foo ID: {queried_foo.id}, Bar ID: {queried_foo.bar.id}")
else:
    print("Foo or associated Bar not found")

# Define the tables
