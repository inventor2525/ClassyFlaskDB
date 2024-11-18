from ClassyFlaskDB.DefaultModel import *
from ClassyFlaskDB.new.FlaskifyDecorator import FlaskifyDecorator
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

# Data objects
@DATA
@dataclass
class Message:
    content: str
    timestamp: datetime = field(default_factory=get_local_time)

@DATA
@dataclass
class StoredMessage:
    message: Message
    response: str

# Service objects
FLASKIFY = FlaskifyDecorator(DATA)

@FLASKIFY
class ChatHistory:
    def __init__(self):
        self.messages: List[StoredMessage] = []
    
    @FLASKIFY.route("/add")
    def add_message(self, message: Message) -> StoredMessage:
        response = f"Echo: {message.content}"
        stored = StoredMessage(message, response)
        self.messages.append(stored)
        return stored
    
    @FLASKIFY.route("/get_all")
    def get_messages(self) -> List[StoredMessage]:
        return self.messages
    
    @FLASKIFY.route("/clear")
    def clear(self) -> None:
        self.messages.clear()

@FLASKIFY
class Calculator:
    def __init__(self, starting_value: float = 0.0):
        self.value = starting_value
    
    @FLASKIFY.route("/add")
    def add(self, x: float) -> float:
        self.value += x
        return self.value
    
    @FLASKIFY.route("/multiply")
    def multiply(self, x: float) -> float:
        self.value *= x
        return self.value
    
    @FLASKIFY.route("/static/add")
    @staticmethod
    def static_add(x: float, y: float) -> float:
        return x + y