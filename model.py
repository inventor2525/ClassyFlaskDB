from dataclasses import dataclass, field
from typing import List
from datetime import datetime
from functools import wraps

@wraps(field)
def saveable_field(*args, internal=False, should_save=True, **kwargs):
	'''
	Extends the dataclasses field decorator to include information about
	how or if saving should take place.
	'''
	if internal:
		kwargs.setdefault('init', False)
		kwargs.setdefault('hash', False)
		kwargs.setdefault('compare', False)
		kwargs.setdefault('repr', False)

	metadata = kwargs.get('metadata', {})
	metadata['should_save'] = should_save
	metadata['internal'] = internal
	kwargs['metadata'] = metadata

	return field(*args, **kwargs)

@wraps(saveable_field)
def internal_field(*args, **kwargs):
	kwargs.setdefault('internal', True)
	kwargs.setdefault('should_save', False)
	return saveable_field(*args, **kwargs)


from dataclasses import dataclass, field, is_dataclass, fields, _POST_INIT_NAME
from functools import wraps



def lazy_hash(cls):
	assert is_dataclass(cls), f"{cls} must be a dataclass to use @lazy_hash, place @dataclass below @lazy_hash to fix this."
	assert "__hash__" in cls.__dict__, f"{cls} must have a __hash__ method to use @lazy_hash, either implement one manually or suggest using @dataclass(unsafe_hash=True)"
	
	cls._fields_dict = {f.name: f for f in fields(cls)}
	
	if "hash" not in cls._fields_dict and "hash" not in cls.__dict__:
		# Add a hash field to the class with 
		original_init = cls.__init__
		original_setattr = cls.__setattr__
		
		@wraps(original_init)
		def new_init(self, *args, **kwargs):
			self._hash_dirty = True
			original_init(self, *args, **kwargs)
		
		@wraps(original_setattr)
		def new_setattr(self, name, value):
			original_setattr(self, name, value)
			if name in cls._fields_dict:
				self._hash_dirty = True
				
		def _calculate_hash(self):
			if self._hash_dirty:
				self._hash_cache = hash(self)
				self._hash_dirty = False
			return self._hash_cache
		
		cls.hash = property(_calculate_hash)
		cls.__init__ = new_init
		cls.__setattr__ = new_setattr
	
	return cls

from enum import Enum
import uuid
import hashlib

class ID_Type(Enum):
	IntAutoIncrement = "int_auto_increment"
	UUIDv4 = "uuidv4"
	PyHash = "py_hash"
	Shaw256 = "sha256"

Default_ID_Type = ID_Type.UUIDv4
def id_field(cls, id_type:ID_Type = Default_ID_Type, field_name:str = "id", primary_key:bool = True):
	'''
	Adds an auto managed id field of a chosen type to the decorated class 
	or lets you select from an existing attribute to use as the id field.
	
	The id field will be used to identify this instance uniquely
	in a database or in json.
	'''
	cls.id_type = id_type
	
	if field_name in cls.__dict__:
		assert hasattr(cls.__dict__[field_name], '__get__'), "field_name must be a field or property."
	else:
		if id_type == ID_Type.IntAutoIncrement:
			cls.next_id = 1
			def _get_auto_increment_id(self):
				if not hasattr(self, '_id'):
					self._id = self.next_id
					self.next_id += 1
				return self._id
			def _set_auto_increment_id(self, value):
				self._id = value
			setattr(cls, '_get_auto_increment_id', _get_auto_increment_id)
			setattr(cls, field_name, property(_get_auto_increment_id, _set_auto_increment_id))

		elif id_type == ID_Type.UUIDv4:
			def _get_uuid(self):
				if not hasattr(self, '_uuid'):
					self._uuid = uuid.uuid4().hex
				return self._uuid
			setattr(cls, '_get_uuid', _get_uuid)
			setattr(cls, field_name, property(
				lambda self: self._uuid,
				lambda self, value: setattr(self, '_uuid', value)
			))

		elif id_type == ID_Type.PyHash:
			setattr(cls, field_name, property(lambda self: hash(self)))

		elif id_type == ID_Type.Sha256:
			if is_dataclass(cls):
				def _get_sha256(self):
					content = '|'.join(str(getattr(self, f.name)) for f in fields(cls))
					return hashlib.sha256(content.encode()).hexdigest()
			else:
				def _get_sha256(self):
					return hashlib.sha256(str(self).encode()).hexdigest()
			setattr(cls, '_get_sha256', _get_sha256)
			setattr(cls, field_name, property(_get_sha256))

	if primary_key:
		cls.primary_key = field_name

	return cls

def id_field(cls, field_name:str = "id", primary_key:bool = True):
	'''
	Adds a id field to the decorated class and specifies if it
	should be the primary key to use in a database.
	'''
	cls.id_type = id_type
	
	if field_name in cls.__dict__:
		assert hasattr(cls.__dict__[field_name], '__get__'), "field_name must be a field or property."
	else:
		def _get_uuid(self):
			if not hasattr(self, '_uuid'):
				self._uuid = uuid.uuid4().hex
			return self._uuid
		setattr(cls, '_get_uuid', _get_uuid)
		setattr(cls, field_name, property(
			lambda self: self._uuid,
			lambda self, value: setattr(self, '_uuid', value)
		))
		
	if primary_key:
		cls.primary_key = field_name

	return cls
	
@id_field
@lazy_hash
@dataclass(unsafe_hash=True)
class MyClass:
	a: int
	b: int
	
	# def __post_init__(self):    #  LINE 1
	# 	self._hash_dirty = True #  LINE 2
obj = MyClass(1, 2)
print(obj.hash)  # Calculates hash
obj.a = 3  # Marks hash as dirty
print(obj.hash)  # Re-calculates hash
obj.b = 3  # Marks hash as dirty
print(obj.hash)  # Re-calculates hash




@dataclass
class MessageSource:
	pass
	
@dataclass
class Message:
	content: str
	
	creation_time: datetime = field(default_factory=datetime.now)
	
	prev_message: "Message" = None
	conversation: "Conversation" = None
	
	source: MessageSource = None
	
	_children: List["Message"] = internal_field(default_factory=list)

@dataclass
class MessageSequence:
	conversation: "Conversation"
	messages: List[Message] = field(default_factory=list)
	
	def add_message(self, message:Message):
		message.prev_message = None if len(self.messages) == 0 else self.messages[-1]
		self.messages.append(message)
	
@dataclass
class Conversation:
	name: str
	description: str
	
	creation_time: datetime = field(default_factory=datetime.now)
	
	message_sequence:MessageSequence = None
	
	_all_messages: List[Message] = internal_field(default_factory=list)
	_root_messages: List[Message] = internal_field(default_factory=list)
	
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

@dataclass
class EditSource(MessageSource):
	original: Message
	new: Message
	new_message_source: MessageSource
	
@dataclass
class ModelSource(MessageSource):
	model_name: str
	model_parameters: dict
	message_sequence: MessageSequence

@dataclass
class UserSource(MessageSource):
	user_name: str = None
	
# a fake conversation with 3 messages to test with:

conv = Conversation("Test Conversation", "A conversation for testing")
conv.add_message( Message("Hello, world!", source=UserSource("Test User")) )
conv.add_message( Message("How are you?", source=UserSource("Test User")) )

print("hello")
