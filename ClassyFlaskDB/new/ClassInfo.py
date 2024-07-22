from ClassyFlaskDB.DATA.ID_Type import ID_Type
from typing import Protocol, Type, Union, Tuple, Set
from dataclasses import fields, Field
import re

class ClassInfo:
	'''
	Info about a class, useful for knowing what the developer wants
	to be serialized on that class.
	'''
	
	field_name = "__class_info__"
	'''The name of the variable a ClassInfo is expected to be stored as on a class type.'''
	
	class Interface(Protocol):
		'''
		Used to document for the IDE what things will be added
		to a class when it has a ClassInfo assigned to it.
		
		Nothing will ever actually be this type.
		'''
		__class_info__:"ClassInfo"
		
	def __init__(self, cls:type, included_fields:Set[str], excluded_fields:Set[str]):
		self.cls = cls
		self.qualname = cls.__qualname__
		self.semi_qualname = self.qualname
		'''
		Similar to cls.__qualname__ except it cleans up type hints for
		nested classes defined inside functions (like in a unit test!).
		
		It's not as specific though so... beware name collisions.
		'''
		while "<locals>." in self.semi_qualname:
			self.semi_qualname = re.sub(r"""^(.*?<locals>\.)?(.*?$)""", r'\2', self.semi_qualname)
		
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
	def has_ClassInfo(type_: Type) -> bool:
		"""
		Checks if the given type has a ClassInfo attribute.
		
		This method is used to determine if a type is decorated with InfoDecorator
		and thus has the necessary metadata for serialization and deserialization.

		:param type_: The type to check for ClassInfo.
		:return: True if the type has ClassInfo, False otherwise.
		"""
		return hasattr(type_, '__class_info__')
	
	@staticmethod
	def get(cls:type) -> 'ClassInfo':
		'''
		Gets the existing ClassInfo on cls.
		'''
		return getattr(cls, ClassInfo.field_name, None)
	
	@staticmethod
	def is_list(field:Field) -> bool:
		'''Returns if this field is a list.'''
		return getattr(field.type, "__origin__", None) is list
	
	@staticmethod
	def is_dict(field:Field) -> Union[Tuple[type,type], bool]:
		'''Returns if this field is a dictionary.'''
		return getattr(field.type, "__origin__", None) is dict
	
	@staticmethod
	def get_list_type(field:Field) -> type:
		return getattr(field.type, "__args__", [None])[0]
	
	@staticmethod
	def get_dict_types(field:Field) -> Tuple[type,type]:
		return getattr(field.type, "__args__", [None,None])

	def is_primary_key(self, field: Field) -> bool:
		return field.name == self.primary_key_name
	
	@staticmethod
	def get_semi_qual_name(type_: Type) -> str:
		if ClassInfo.has_ClassInfo(type_):
			return ClassInfo.get(type_).semi_qualname.replace('.', '_')
		return type_.__name__