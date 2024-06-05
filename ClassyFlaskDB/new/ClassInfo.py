from ClassyFlaskDB.DATA.ID_Type import ID_Type
from dataclasses import dataclass, fields, field, Field
from typing import Dict, Any, Type, List, Union, ForwardRef, Tuple, Set, Iterable, overload, TypeVar, Callable
import re

class ClassInfo:
	field_name = "__class_info__"
	
	def __init__(self, cls:type, included_fields:Set[str], excluded_fields:Set[str]):
		self.cls = cls
		self.qualname = cls.__qualname__
		self.semi_qualname = re.sub(r"""^(.*?<locals>\.)?(.*?$)""", r'\2', cls.__qualname__)
		'''
		Similar to cls.__qualname__ except it cleans up type hints for
		nested classes defined inside functions (like in a unit test!).
		
		It's not as specific though so... beware name collisions.
		'''
		
		# Get fields:
		self.all_fields = fields(cls)
		self._included_fields = included_fields
		self._excluded_fields = excluded_fields
		
		if len(included_fields)==0:
			included_fields = set([f.name for f in self.all_fields])
		self.fields = {f.name:f for f in self.all_fields if f.name in included_fields and f.name not in excluded_fields}
		'''
		Fields that will be serialized and deserialized.
		'''
		
		# Get the name of the primary key:
		self.id_type = ID_Type.USER_SUPPLIED
		self.primary_key_name = getattr(cls, "__primary_key_name__", None)
		if self.primary_key_name is None:
			for f in self.fields.values():
				if getattr(f.metadata, "primary_key", False):
					self.primary_key_name = f.name
	
	@property
	def parent_classes(self) -> 'ClassInfo':
		return [
			getattr(base,ClassInfo.field_name)
			for base in self.cls.__bases__ 
			if hasattr(base, ClassInfo.field_name)
		]
	
	@staticmethod
	def has_ClassInfo(field:Field) -> bool:
		'''
		Checks if the type of field is itself also a InfoDecorator decorated class.
		
		In other worlds, most commonly, should we drill into it when iterating, or treat
		it as it's own separate type with a custom serializer like a datetime.
		'''
		return hasattr(field.type, ClassInfo.field_name)
	
	@staticmethod
	def get(cls:type) -> 'ClassInfo':
		'''
		Gets the existing ClassInfo on cls.
		'''
		return getattr(cls, ClassInfo.field_name, None)
	
	@staticmethod
	def is_list(field:Field) -> Union[type, bool]:
		'''Returns the type of list if it is one, and False if it's not a list.'''
		if getattr(field.type, "__origin__", None) is list:
			return getattr(field.type, "__args__", [None])[0]
		return False
	
	@staticmethod
	def is_dict(field:Field) -> Union[Tuple[type,type], bool]:
		'''Returns the types of key and value for the dict if it is one, and False if it's not a dict.'''
		if getattr(field.type, "__origin__", None) is dict:
			return getattr(field.type, "__args__", [None,None])
		return False