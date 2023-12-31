from ClassyFlaskDB.DATA import *

from datetime import datetime
from typing import List

DATA = DATADecorator()

@DATA
class MessageSource:
	pass
	
@DATA
class Message:
	content: str
	
	creation_time: datetime = field(default_factory=datetime.now)
	
	prev_message: "Message" = None
	conversation: "Conversation" = None
	
	source: MessageSource = None
	
	_children: List["Message"] = field(default_factory=list)

@DATA
class MessageSequence:
	conversation: "Conversation"
	messages: List[Message] = field(default_factory=list)
	
	def add_message(self, message:Message):
		message.prev_message = None if len(self.messages) == 0 else self.messages[-1]
		self.messages.append(message)
	
@DATA
class Conversation:
	name: str
	description: str
	
	creation_time: datetime = field(default_factory=datetime.now)
	
	message_sequence:MessageSequence = None
	
	_all_messages: List[Message] = field(default_factory=list)
	_root_messages: List[Message] = field(default_factory=list)
	
	def __post_init__(self, message_sequence:MessageSequence = None):
		if message_sequence is None:
			self.message_sequence = MessageSequence(self)
			
	def add_message(self, message:Message):
		self._all_messages.append(message)
		self.message_sequence.add_message(message)
		if message.prev_message is None:
			self._root_messages.append(message)
		else:
			message.prev_message._children.append(message)
		message.conversation = self

@DATA
class EditSource(MessageSource):
	original: Message
	new: Message = None
	new_message_source: MessageSource = None
	pass
	
@DATA
class ModelSource(MessageSource):
	model_name: str
	model_parameters: dict
	message_sequence: MessageSequence

@DATA
class UserSource(MessageSource):
	user_name: str = None

DATA.finalize()
data_engine = DATAEngine(DATA, engine_str='sqlite:///my_database4.db')

# Example usage
m1 = Message(content='!', source=UserSource(user_name='Fred'))
data_engine.merge(m1)

conversation = Conversation(name='Conversation 1', description='First conversation')
conversation.add_message(Message(content='Hello', source=UserSource(user_name='George')))
conversation.add_message(Message(content='World', source=UserSource(user_name='Alice')))
conversation.add_message(Message(content='!', source=EditSource(original=m1, new_message_source=UserSource(user_name='Bob'))))
conversation.message_sequence.messages[2].source.new = conversation.message_sequence.messages[2]
data_engine.merge(conversation)

import json
from json import JSONEncoder

class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return JSONEncoder.default(self, obj)
	
print(json.dumps(data_engine.to_json(), indent=4, cls=DateTimeEncoder))

# Query
with data_engine.session() as session:
	queried_conversation = session.query(Conversation).filter_by(name="Conversation 1").first()
	print("Conversation:", queried_conversation.name)