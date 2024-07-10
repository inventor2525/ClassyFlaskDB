from ClassyFlaskDB.new.SQLStorageEngine import *

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