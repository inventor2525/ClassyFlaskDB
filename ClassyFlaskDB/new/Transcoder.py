from .ClassInfo import *
from dataclasses import dataclass, Field
from abc import ABC, abstractmethod, abstractclassmethod
from .Args import *

@dataclass
class Transcoder(ABC):
	@abstractclassmethod
	def validate(cls, type:Type) -> bool:
		'''
		Returns true if this Transcoder type can be used with this Field.
		'''
		return False
	
	@abstractclassmethod
	def setup(cls, classInfo:ClassInfo, field:Field) -> 'Transcoder':
		'''
		Creates anything needed, like columns in a table, or relationships
		between them (or what ever makes sense in the case of this storage engine).
		'''
		pass
	
	@abstractmethod
	def _merge(self, merge:MergeArgs, obj:Interface) -> None:
		pass
	
	@classmethod
	def merge(self, merge:MergeArgs, obj:Interface) -> None:
		if obj.is_dirty(merge.is_dirty):
			self._merge(merge, obj)
			obj.clear_dirty(merge.is_dirty)
	
	def get_hashing_value(cls, value:Any) -> Any:
		return value