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

Grandchild1_table = Table(
    'grandchild1', mapper_registry.metadata,
    Column('id', Integer, ForeignKey('child1.id'), primary_key=True),
    Column('favorite_color', String)
)

Holder_table = Table(
    'holder', mapper_registry.metadata,
    Column('id', Integer, primary_key=True),
    Column('child_id', Integer, ForeignKey('baseclass.id'))
)

@dataclass
class BaseClass:
    id: int

    def __str__(self) -> str:
        return f"Type: {self.__class__.__name__}, ID: {self.id}"

@dataclass
class Child1(BaseClass):
    name: str
    age: int

    def __str__(self) -> str:
        return super().__str__() + f", Name: {self.name}, Age: {self.age}"

@dataclass
class Child2(BaseClass):
    description: str
    height: float

    def __str__(self) -> str:
        return super().__str__() + f", Description: {self.description}, Height: {self.height}"

@dataclass
class Grandchild1(Child1):
    favorite_color: str

    def __str__(self) -> str:
        return super().__str__() + f", Favorite Color: {self.favorite_color}"


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
    polymorphic_identity='baseclass',
    polymorphic_on=BaseClass_table.c.type
)

mapper_registry.map_imperatively(Child1, Child1_table, 
    inherits=BaseClass, 
    polymorphic_identity='Child1'
)

mapper_registry.map_imperatively(Child2, Child2_table, 
    inherits=BaseClass, 
    polymorphic_identity='Child2'
)
mapper_registry.map_imperatively(Grandchild1, Grandchild1_table, 
    inherits=Child1, 
    polymorphic_identity='Grandchild1'
)

mapper_registry.map_imperatively(Holder, Holder_table, 
    properties={
        'child': relationship(BaseClass, uselist=False)
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
session.merge(child1)
session.merge(child2)
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
session.merge(holder1)
session.merge(holder2)
session.commit()

grandchild1 = Grandchild1(id=3, name="Bob", age=12, favorite_color="Blue")

# Add the grandchild to the session
session.merge(grandchild1)
session.commit()

# Create Holder instance for the grandchild
holder3 = Holder(id=3, child=grandchild1)

# Add the Holder instance to the session
session.merge(holder3)
session.commit()

# Query the Holder table and load the associated children
holders = session.query(Holder).all()

for holder in holders:
    print(f"Holder ID: {holder.id}")
    print(f"Child: {holder.child}")



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
    print(f"Child: {holder.child}")