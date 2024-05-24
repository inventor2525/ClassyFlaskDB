from ClassyFlaskDB.DefaultModel import *
from datetime import datetime
from typing import List
import tzlocal

@DATA
@dataclass
class MessageSource(Source):
	pass
	
@DATA
@dataclass
class Message(Object):
	content: str
	
	prev_message: "Message" = None
	conversation: "Conversation" = None
	
	_children: List["Message"] = field(default_factory=list)

@DATA(generated_id_type=ID_Type.HASHID, hashed_fields=["messages"])
@dataclass
class MessageSequence(Object):
	conversation: "Conversation"
	messages: List[Message] = field(default_factory=list)
	
	def add_message(self, message:Message):
		message.prev_message = None if len(self.messages) == 0 else self.messages[-1]
		self.messages.append(message)
		self.new_id()
	
@DATA
@dataclass
class Conversation(Object):
	name: str
	description: str
	
	message_sequence:MessageSequence = None
	
	_all_messages: List[Message] = field(default_factory=list)
	_root_messages: List[Message] = field(default_factory=list)
	
	def __post_init__(self, message_sequence:MessageSequence = None):
		if message_sequence is None:
			self.message_sequence = MessageSequence(self)
			
	def add_message(self, message:Message):
		# self._all_messages.append(message)
		old_message_sequence = self.message_sequence.messages
		self.message_sequence = MessageSequence(self)
		self.message_sequence.messages.extend(old_message_sequence)
		self.message_sequence.add_message(message)
		# if message.prev_message is None:
		# 	self._root_messages.append(message)
		# else:
		# 	message.prev_message._children.append(message)
		message.conversation = self

@DATA
@dataclass
class EditSource(Source):
	original: Message
	new: Message = None
	new_message_source: MessageSource = None
	pass
	
@DATA
@dataclass
class ModelSource(Source):
	model_name: str
	model_parameters: dict
	message_sequence: MessageSequence

@DATA
@dataclass
class UserSource(Source):
	user_name: str = None
