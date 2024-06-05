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

T = TypeVar('T')
@dataclass
class InfoDecorator:
	decorated_classes:List[type] = field(default_factory=list, kw_only=True)
	registry:Dict[str, type] = field(default_factory=dict, kw_only=True)
	
	@overload
	def __call__(self, cls:Type[T]) -> Type[T]:
		pass
	@overload
	def __call__(self, included_fields: Iterable[str] = [], excluded_fields: Iterable[str] = []) -> Callable[[Type[T]], Type[T]]:
		pass
	def __call__(self, *args, **kwargs):
		if len(args) == 1 and isinstance(args[0], type):
			return self.decorate(args[0])
		else:
			return lambda cls: self.decorate(cls, *args, **kwargs)

	def decorate(self, cls: Type[T], included_fields: Iterable[str] = [], excluded_fields: Iterable[str]=[]) -> Type[T]:
		class_info = ClassInfo(cls, set(included_fields), set(excluded_fields))
		setattr(cls, ClassInfo.field_name, class_info)
		self.registry[class_info.semi_qualname] = cls
		return cls

	def finalize(self):
		open_list = []
		for cls in self.registry.values():
			classInfo = getattr(cls, ClassInfo.field_name)
			for f in classInfo.fields.values():
				f.type = self._resolve_type(f.type)
				open_list.append(f.type)

		while open_list:
			type_ = open_list.pop(0)
			if hasattr(type_, '__origin__') and hasattr(type_, '__args__'):
				type_.__args__ = tuple(self._resolve_type(arg) for arg in type_.__args__)
				open_list.extend(type_.__args__)

	def _resolve_type(self, type_):
		if isinstance(type_, ForwardRef):
			return self.registry.get(type_.__forward_arg__, type_)
		elif isinstance(type_, str):
			return self.registry.get(type_, type_)
		else:
			return type_

if __name__ == "__main__":
	INFO = InfoDecorator()

	@INFO(excluded_fields=["my_int"])
	@dataclass
	class Foo:
		my_list: List[int]
		my_dict: Dict[str, 'Bar']
		my_union: Union[int, str]
		my_int: int
		my_str: str
		my_forward_ref: 'Bar.Baz'
		my_forward_ref2: List[Dict[Tuple['Bar.Baz'], 'Bar']]

	@INFO
	@dataclass
	class Bar:
		@INFO(["my_foo"])
		@dataclass
		class Baz:
			baz: str
			my_foo: 'Foo' = field(default= Foo([],{}, 42, 1, "Hello World", None, []))

	print(Foo.__class_info__.field_types)
	print(Bar.__class_info__.field_types)
	print(Bar.Baz.__class_info__.field_types)

	INFO.finalize()

	print(Foo.__class_info__.field_types)
	print(Bar.__class_info__.field_types)

	print(Bar.Baz.__class_info__.field_types)