from ClassyFlaskDB.Decorators.to_sql import to_sql

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Table, ForeignKey, Float
from sqlalchemy.orm import registry, relationship, sessionmaker
from sqlalchemy.ext.declarative import declared_attr, DeclarativeMeta
from sqlalchemy import inspect
from sqlalchemy.orm import mapper
from sqlalchemy.orm import relationship

from ClassyFlaskDB.Decorators.LazyDecorator import LazyDecorator
from ClassyFlaskDB.Decorators.capture_field_info import capture_field_info, FieldInfo, FieldsInfo
from ClassyFlaskDB.DATA import DATA

from dataclasses import dataclass, field

from typing import List

# Define an engine and base
engine = create_engine('sqlite:///my_database3.db')

@DATA
class Bar:
    id: str

@DATA
class Bar2(Bar):
    name: str

@DATA
class Foo:
    id: int
    bar: Bar
    bars: List[Bar] = field(default_factory=list)
DATA.finalize(engine).metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Example usage
bar_instance = Bar(id='bar1')
foo_instance = Foo(id=1, bar=bar_instance)
foo_instance.bars.append(Bar(id='bar2'))
foo_instance.bars.append(Bar(id='bar3'))
session.merge(foo_instance)
session.commit()

bar_instance = Bar2(id='bar4', name='Bar 4')
foo_instance = Foo(id=2, bar=bar_instance)
foo_instance.bars.append(Bar2(id='bar5', name='Bar 5'))
foo_instance.bars.append(Bar(id='bar6'))
session.merge(foo_instance)
session.commit()

import json
print(json.dumps(foo_instance.to_json(), indent=4))

# Query
queried_foo = session.query(Foo).filter_by(id=1).first()

print(json.dumps(DATA.dump_as_json(engine, session), indent=4))
if queried_foo and queried_foo.bar:
    print(f"Foo ID: {queried_foo.id}, Bar ID: {queried_foo.bar.id}")
else:
    print("Foo or associated Bar not found")