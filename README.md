## ClassyFlaskDB

**Welcome to ClassyFlaskDB: A Python Library for Simplified Database Interactions**

ClassyFlaskDB is a Python library that provides a simple and intuitive way to interact with databases using SQLAlchemy which is great for prototyping. With ClassyFlaskDB, you can define your database schema and python model classes simultaneously using the same syntax as [dataclasses](https://docs.python.org/3/library/dataclasses.html), making it easy to get started with database development.

ClassyFlaskDB is not a full ORM, it sits on-top of SQLAlchemy to make prototyping easier.
## Getting Started

**Installation**

To use ClassyFlaskDB, you'll need to install it using pip:
```
#clone the repo
#cd into the repo
pip install -e ./
```

Note that ClassyFlaskDB is still in development, hence the need to install it in editable mode without PyPI.

**Defining Your Database Schema**

In ClassyFlaskDB, you define your database schema using Python classes and decorators. Here's an example:
```python
from classyflaskdb import DATADecorator, DATAEngine

DATA = DATADecorator() # Create a decorator instance (this is useful if you have multiple schemas you want to keep separate)
@DATA
class User:
    name: str
    email: str

@DATA
class Post:
    title: str
    content: str
    user: User
```
In this example, we define two classes: `User` and `Post`. The `@DATADecorator()` decorator tells ClassyFlaskDB to create a database table for each class, with columns corresponding to the class attributes based on their type annotations, but it also adds a auto generated 'auto_id' column as the primary key that defaults to a UUID4.

You can also specify the primary key by adding a `__primary_key__` attribute to the class or use field(metadata={'primary_key': True}) like a @dataclass field.
```python
@DATA
class User:
    __primary_key__ = 'email'
    name: str
    email: str
```
or
```python
from dataclasses import field

@DATA
class User:
    name: str
    email: str = field(metadata={'primary_key': True})
```

**Creating a Database Engine**

To interact with your database, you'll need to create a `DATAEngine` instance:
```python
data_engine = DATAEngine(DATA)
```
This is the point where all your @DATA decorated classes are registered with the engine and their tables are created in the database. So they must be imported at this point!

## CRUD Operations

Here are some examples of CRUD operations using ClassyFlaskDB:

**Create**
```python
user = User(name="John Doe", email="johndoe@example.com")
data_engine.merge(user)
```
**Read**
```python
with data_engine.session() as session:
	users = session.query(User).all()
	for user in users:
		print(user.name, user.email)
```
**Update**
```python
with data_engine.session() as session:
	user = session.query(User).filter_by(name="John Doe").first()
	user.email = "johndoe2@example.com"
	data_engine.merge(user)
```
**Delete**
```python
with data_engine.session() as session:
	user = session.query(User).filter_by(name="John Doe").first()
	data_engine.delete(user)
```
## Comparison with SQLAlchemy

Here's an example of how you would define a similar database schema using SQLAlchemy:
```python
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)

class Post(Base):
    __tablename__ = 'posts'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship(User)

engine = create_engine('sqlite:///example.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

# Create a user
user = User(name="John Doe", email="johndoe@example.com")
session.add(user)
session.commit()

# Query users
users = session.query(User).all()
for user in users:
    print(user.name, user.email)
```
As you can see, ClassyFlaskDB provides a much simpler and more intuitive way to define your database schema and perform CRUD operations.

## Additional Features

ClassyFlaskDB provides several additional features, including:

* **Automatic ID generation**: ClassyFlaskDB can automatically generate IDs for your objects using UUID or hash. With hash, you can call new_id() to get the new hash, or pass true and propagate to all children.
* **Relationships**: ClassyFlaskDB supports relationships between objects, including one-to-one, one-to-many, and many-to-many relationships.
* **Subclassing**: ClassyFlaskDB supports subclassing of database classes, allowing you to define complex inheritance hierarchies. Doing this will automatically create a table for the subclass with a foreign key to the parent class.
* **Serialization**: ClassyFlaskDB provides built-in support for serializing objects to JSON and importing from JSON.
* **Auto Updates**: ClassyFlaskDB automatically adjusts the schema as you change the python classes, making it great for prototyping. (Auto backups are kept when using sql lite!)

## Examples
There are plenty of examples in the examples folder, including a simple flask app that has some additional decorators for server & client code generation from local code using decorators.

You can also look at the tests for more examples.

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Conclusion

ClassyFlaskDB is a powerful and intuitive library for interacting with databases in Python. With its simple and flexible API, you can quickly and easily define your database schema and perform CRUD operations. Whether you're building a small web application or a large-scale enterprise system, ClassyFlaskDB is a great choice for your database needs.