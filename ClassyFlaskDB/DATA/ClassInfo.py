from dataclasses import dataclass, fields, field
from typing import Dict, Any, Type, List, Union, ForwardRef, Tuple
import re

class ClassInfo:
	def __init__(self, cls):
		self.cls = cls
		self.qualname = cls.__qualname__
		self.semi_qualname = re.sub(r"""^(.*?<locals>\.)?(.*?$)""", r'\2', cls.__qualname__)
		'''
		Similar to cls.__qualname__ except it cleans up type hints for
		nested classes defined inside functions (like in a unit test!).
		
		It's not as specific though so... beware name collisions.
		'''
		self.fields = [f for f in fields(cls) if f.type or f.default or f.metadata]
	
	@property
	def field_types(self) -> Dict[str, type]:
		self.semi_qualname
		return {f.name: f.type for f in self.fields}

@dataclass
class InfoDecorator:
	decorated_classes:List[type] = field(default_factory=list)
	registry:Dict[str, type] = field(default_factory=dict)

	def __init__(self):
		self.registry = {}

	def __call__(self, cls):
		cls.__class_info__ = ClassInfo(cls)
		self.registry[cls.__class_info__.semi_qualname] = cls
		return cls

	def finalize(self):
		open_list = []
		for cls in self.registry.values():
			for f in cls.__class_info__.fields:
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

	@INFO
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
		@INFO
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