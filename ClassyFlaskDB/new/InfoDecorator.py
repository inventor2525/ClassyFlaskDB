from .ClassInfo import *

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