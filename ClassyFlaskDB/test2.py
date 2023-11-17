from sqlalchemy import Integer, String, Float, Column, ForeignKey
from sqlalchemy.orm import relationship, mapper, joinedload
from dataclasses import dataclass
from sqlalchemy import Table
from sqlalchemy.orm import registry

mapper_registry = registry()

# Define the tables
BaseClass_table = Table(
    'baseclass', mapper_registry.metadata,
    Column('id', Integer, primary_key=True),
    Column('type', String)  # Polymorphic discriminator
)

Child1_table = Table(
    'child1', mapper_registry.metadata,
    Column('id', Integer, ForeignKey('baseclass.id'), primary_key=True),
    Column('name', String),
    Column('age', Integer)
)

Child2_table = Table(
    'child2', mapper_registry.metadata,
    Column('id', Integer, ForeignKey('baseclass.id'), primary_key=True),
    Column('description', String),
    Column('height', Float)
)

Holder_table = Table(
    'holder', mapper_registry.metadata,
    Column('id', Integer, primary_key=True),
    Column('child_id', Integer, ForeignKey('baseclass.id')),
    Column('child_type', String)
)

@dataclass
class BaseClass:
    id: int

@dataclass
class Child1(BaseClass):
    name: str
    age: int

@dataclass
class Child2(BaseClass):
    description: str
    height: float

@dataclass
class Holder:
    id: int
    child: BaseClass

from marshmallow_dataclass import class_schema
import json

# Define Marshmallow schemas for data classes
Child1Schema = class_schema(Child1)()
Child2Schema = class_schema(Child2)()
BaseClassSchema = class_schema(BaseClass)()
HolderSchema = class_schema(Holder)()


# Configure mappers
mapper_registry.map_imperatively(BaseClass, BaseClass_table, 
    properties={
        'child1': relationship(Child1, uselist=False),
        'child2': relationship(Child2, uselist=False)
    },
    polymorphic_identity='baseclass',
    polymorphic_on=BaseClass_table.c.type
)

mapper_registry.map_imperatively(Child1, Child1_table, 
    inherits=BaseClass, 
    polymorphic_identity='child1'
)

mapper_registry.map_imperatively(Child2, Child2_table, 
    inherits=BaseClass, 
    polymorphic_identity='child2'
)

mapper_registry.map_imperatively(Holder, Holder_table, 
    properties={
        'child': relationship(BaseClass, 
                              lazy='joined', 
                              join_depth=1)
    }
)


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Create the engine and session
engine = create_engine('sqlite:///my_database2.db')
session = sessionmaker(bind=engine)()

# Create the tables
mapper_registry.metadata.create_all(engine)

# Create instances of Child1 and Child2
child1 = Child1(id=1, name="Alice", age=30)
child2 = Child2(id=2, description="Tall person", height=6.1)

# Add the children to the session
session.add(child1)
session.add(child2)
session.commit()

# Create Holder instances
holder1 = Holder(id=1, child=child1)
holder2 = Holder(id=2, child=child2)


# Example of serialization
holder_json = HolderSchema.dumps(holder2)
print("Holder JSON:", holder_json)

# Example of deserialization
holder = HolderSchema.loads(holder_json)
print("Holder:", holder)

# Add the Holder instances to the session
session.add(holder1)
session.add(holder2)
session.commit()

# Query the Holder table and load the associated children
holders = session.query(Holder).all()

for holder in holders:
    print(f"Holder ID: {holder.id}")
    if isinstance(holder.child, Child1):
        print(f"Child Type: Child1, Name: {holder.child.name}, Age: {holder.child.age}")
    elif isinstance(holder.child, Child2):
        print(f"Child Type: Child2, Description: {holder.child.description}, Height: {holder.child.height}")



import json
from sqlalchemy import MetaData

def dump_db_to_json(session):
    metadata = MetaData()
    metadata.reflect(bind=session.bind)
    db_data = {}

    for table_name, table in metadata.tables.items():
        db_data[table_name] = [row._asdict() for row in session.execute(table.select()).fetchall()]

    return json.dumps(db_data, indent=4)

# Usage Example
json_data = dump_db_to_json(session)
print(json_data)


from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import json

def load_json_into_db(json_data, session):
    metadata = MetaData()
    metadata.reflect(bind=session.bind)
    db_data = json.loads(json_data)

    for table_name, rows in db_data.items():
        table = metadata.tables[table_name]
        for row_data in rows:
            session.execute(table.insert(), row_data)

    session.commit()
    return session

# Example Usage
# Assuming `json_data` is the JSON string from the previous dump
engine = create_engine('sqlite:///:memory:')
mapper_registry.metadata.create_all(engine)  # Assuming tables are already defined in mapper_registry
Session = sessionmaker(bind=engine)
session = Session()

new_session = load_json_into_db(json_data, session)

# Verify the loaded data
holders = new_session.query(Holder).all()

for holder in holders:
    print(f"Holder ID: {holder.id}")
    if isinstance(holder.child, Child1):
        print(f"Child Type: Child1, Name: {holder.child.name}, Age: {holder.child.age}")
    elif isinstance(holder.child, Child2):
        print(f"Child Type: Child2, Description: {holder.child.description}, Height: {holder.child.height}")