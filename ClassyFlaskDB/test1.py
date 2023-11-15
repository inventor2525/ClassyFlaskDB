from dataclasses import dataclass, field
from datetime import datetime
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import registry, relationship, sessionmaker

# Define an engine and base
engine = create_engine('sqlite:///:memory:')
mapper_registry = registry()

# Define the tables
message_table = Table(
    'message', mapper_registry.metadata,
    Column('id', String, primary_key=True),
    Column('content', String),
    Column('creation_time', String)
)

conversation_table = Table(
    'conversation', mapper_registry.metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('description', String),
    Column('creation_time', String)
)

# Association table for the many-to-many relationship
conversation_message_table = Table(
    'conversation_message', mapper_registry.metadata,
    Column('conversation_id', Integer, ForeignKey('conversation.id'), primary_key=True),
    Column('message_id', String, ForeignKey('message.id'), primary_key=True)
)

@dataclass
class Message:
    id: str
    content: str
    creation_time: datetime = field(default_factory=datetime.now)

@dataclass
class Conversation:
    id: int
    name: str
    description: str
    creation_time: datetime = field(default_factory=datetime.now)
    messages: List[Message] = field(default_factory=list)


@dataclass
class BaseClass:
    id :int

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
    id :int
    child: BaseClass

BaseClass_table = Table(
    'baseclass', mapper_registry.metadata,
    Column('id', Integer, primary_key=True)
)

Child1_table = Table(
    'child1', mapper_registry.metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('age', Integer)
)

Child2_table = Table(
    'child2', mapper_registry.metadata,
    Column('id', Integer, primary_key=True),
    Column('description', String),
    Column('height', Float)
)

Holder_table = Table(
    'holder', mapper_registry.metadata,
    Column('id', Integer, primary_key=True),
    Column('child_id', Integer),
    Column('child_type', String)
)

# Configure mappers
mapper_registry.map_imperatively(Message, message_table)

mapper_registry.map_imperatively(Conversation, conversation_table, properties={
    'messages': relationship(
        'Message',
        secondary=conversation_message_table)
})
# Create tables
mapper_registry.metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

# Example usage
conversation1 = Conversation(id=1, name="Test Conversation 1", description="First test conversation")
conversation2 = Conversation(id=2, name="Test Conversation 2", description="Second test conversation")
message1 = Message(id="msg1", content="Hello first World!")
message2 = Message(id="msg2", content="Hello second World!")

conversation1.messages.append(message1)
conversation2.messages.append(message1)
conversation2.messages.append(message2)

# Add to session and commit
session.add_all([conversation1, conversation2])
session.commit()

# Query
queried_conversation = session.query(Conversation).filter_by(name="Test Conversation 2").first()
print("Conversation:", queried_conversation.name)
for msg in queried_conversation.messages:
    print("Message:", msg.content)
