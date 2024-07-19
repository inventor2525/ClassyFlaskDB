from typing import List, Dict, Any, Union, Callable, Type, TypeVar
from dataclasses import dataclass, Field, field
from .ClassInfo import *

T = TypeVar('T')

@dataclass
class DirtyDecorator:
	class Interface:
		_dirty:bool
		def _is_dirty(self, isDirt:Dict[int, bool]) -> bool:
			pass
		
		def is_dirty(self, isDirt:Dict[int, bool]) -> bool:
			pass
		
		def clear_dirty(self, isDirt:Dict[int, bool]) -> Any:
			pass
	
	def __call__(self, cls:Type[T]) -> Union[Type[T], "DirtyDecorator.Interface"]:
		def list_is_dirty(self:list, isDirt:Dict[int, bool]) -> bool:
			'''
			_is_dirty for lists
			'''
			for element in self:
				if hasattr(element, "is_dirty"):
					if element.is_dirty(isDirt):
						return True
			return False
		
		def dict_is_dirty(self:dict, isDirt:Dict[int, bool]) -> bool:
			'''
			_is_dirty for dictionaries
			'''
			for key,value in self.items():
				if hasattr(key, "is_dirty"):
					if key.is_dirty(isDirt):
						return True
				if hasattr(value, "is_dirty"):
					if value.is_dirty(isDirt):
						return True
			return False
		
		def obj_is_dirty(self:ClassInfo.Interface, isDirt:Dict[int, bool]) -> bool:
			'''
			_is_dirty for objects
			'''
			for f in self.__class_info__.fields:
				value = object.__getattribute__(self, )
				if hasattr(value, "is_dirty"):
					if value.is_dirty(isDirt):
						return True
			return False
		
		def is_dirty(self, isDirt:Dict[int, bool]) -> bool:
			if self._dirty:
				return True
			if id(self) in isDirt:
				return isDirt[id(self)]
			dirty = self._is_dirty(isDirt)
			isDirt[id(self)] = dirty
			return dirty
		
		def clear_dirty(self, isDirt:Dict[int, bool]) -> Any:
			self._dirty = False
			isDirt[id(self)]=False
		
		if issubclass(cls, list):
			setattr(cls, "_is_dirty", list_is_dirty)
		elif issubclass(cls, dict):
			setattr(cls, "_is_dirty", dict_is_dirty)
		elif hasattr(cls, ClassInfo.field_name):
			setattr(cls, "_is_dirty", obj_is_dirty)
		else:
			raise ValueError(f"{cls} not supported by DirtyDecorator")
		
		setattr(cls, "_dirty", True)
		setattr(cls, "is_dirty", is_dirty)
		setattr(cls, "clear_dirty", clear_dirty)
		return cls

DirtyDecorator = DirtyDecorator()