from .ClassInfo import *
from .StorageEngineContext import *
from dataclasses import dataclass, Field
from typing import TypeVar, Generic, Any
from abc import ABC, abstractmethod, abstractclassmethod
from .ClassInfo import ClassInfo

T = TypeVar('T')

@dataclass
class Transcoder(Generic[T], ABC):
	'''
	Stores state information and what is needed for a field
	to be lazily loaded from a storage engine
	'''
	context:StorageEngineContext
	'''Any state information about the storage engine we need to... not load the same thing over again and such.'''
	classInfo:ClassInfo
	'''Info about the type of object who's field we manage is on.'''
	field:Field
	'''The dataclasses.field (and all metadata) this transcoder refers to.'''
	dirty:bool = False
	'''Indicates that the value needs to be saved.'''
	valid:bool = False
	'''Indicates if the value was either set or loaded. When false this means the value must be loaded first.'''
	loaded:bool = False
	'''Indicates if there is a value loaded from file.'''
	
	mem_value:T = None
	saved_value:T = None
	
	def set(self, value:T):
		if not self.loaded or value != self.saved_value:
			self.dirty = True
			
		if value != self.mem_value:
			self.mem_value = value
		self.valid = True
	
	def get(self) -> T:
		if self.valid:
			return self.mem_value
		if self.loaded:
			return self.saved_value
		#TODO: Load! from storage engine the whole obj 1 level deep
		self.loaded = True
		self.dirty = False
		return self.saved_value
	
	@abstractclassmethod
	def validate(cls, classInfo:ClassInfo, field:Field) -> bool:
		'''
		Returns true if this Transcoder type can be used with this Field.
		'''
		return False
	
	def setup(cls, classInfo:ClassInfo, field:Field):
		'''
		Creates anything needed, like columns in a table, or relationships
		between them (or what ever makes sense in the case of this storage engine).
		'''
		pass
	
	def encode(cls, value:T) -> Any:
		return value
	
	def decode(cls, encoded:Any) -> T:
		return encoded
	
	def get_hashing_value(cls, value:T) -> Any:
		return value