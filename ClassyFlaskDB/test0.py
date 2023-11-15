from sqlalchemy import create_engine, Table, Column, Integer, String, ForeignKey
from sqlalchemy.orm import registry, relationship, sessionmaker
from dataclasses import dataclass

# Define the registry
mapper_registry = registry()

# Define the tables
Foo_table = Table(
    'foo', mapper_registry.metadata,
    Column('id', Integer, primary_key=True),
    Column('bar_id', String, ForeignKey('bar.id'))  # For establishing the relationship
)

Bar_table = Table(
    'bar', mapper_registry.metadata,
    Column('id', String, primary_key=True)
)

@dataclass
class Bar:
    id: str

@dataclass
class Foo:
    id: int
    bar: Bar

# Configure mappers
mapper_registry.map_imperatively(Foo, Foo_table, properties={
    'bar': relationship(Bar, uselist=False)
})
mapper_registry.map_imperatively(Bar, Bar_table)

# Create the engine and session
engine = create_engine('sqlite:///:memory:')
# Create tables
mapper_registry.metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Example usage
bar_instance = Bar(id='bar1')
foo_instance = Foo(id=1, bar=bar_instance)

# Add to the session and commit
session.add_all([foo_instance, bar_instance])
session.commit()

# Query
queried_foo = session.query(Foo).filter_by(id=1).first()
if queried_foo and queried_foo.bar:
    print(f"Foo ID: {queried_foo.id}, Bar ID: {queried_foo.bar.id}")
else:
    print("Foo or associated Bar not found")