from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ClassyFlaskDB.DATA import DATA

from dataclasses import field
from datetime import datetime
from typing import List

engine = create_engine('sqlite:///:memory:', echo=True)

@DATA
class MessageSource:
	pass
	
@DATA
class Message:
	content: str = None
	source: MessageSource = None
	
	# creation_time: datetime = field(default_factory=datetime.now)
	
	prev_message: "Message" = None
	conversation: "Conversation" = None
	
	_children: List["Message"] = field(default_factory=list)

@DATA
class MessageSequence:
	conversation: "Conversation" = None
	messages: List[Message] = field(default_factory=list)
	
	def add_message(self, message:Message):
		message.prev_message = None if len(self.messages) == 0 else self.messages[-1]
		self.messages.append(message)
	
@DATA
class Conversation:
	name: str = None
	description: str = None
	
	# creation_time: datetime = field(default_factory=datetime.now)
	
	message_sequence:MessageSequence = None
	
	_all_messages: List[Message] = field(default_factory=list)
	_root_messages: List[Message] = field(default_factory=list)
	
	def __post_init__(self, message_sequence:MessageSequence = None):
		if message_sequence is None:
			self.message_sequence = MessageSequence(self)
			
	def add_message(self, message:Message):
		# self._all_messages.append(message)
		self.message_sequence.add_message(message)
		# if message.prev_message is None:
		# 	self._root_messages.append(message)
		# else:
		# 	message.prev_message._children.append(message)
		message.conversation = self

@DATA
class EditSource(MessageSource):
	original: Message = None
	new: Message = None
	new_message_source: MessageSource = None
	pass
	
@DATA
class ModelSource(MessageSource):
	model_name: str = None
	model_parameters: dict = field(default_factory=dict)
	message_sequence: MessageSequence = None

@DATA
class UserSource(MessageSource):
	user_name: str = None

DATA.finalize(engine, globals()).metadata.create_all(engine)
