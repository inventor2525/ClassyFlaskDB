from typing import Any, Callable, Generic, TypeVar, Optional

T = TypeVar('T')

class AutoProperty(Generic[T]):
	_uninitialized = object()

	def __init__(self, use_getter: bool = False, nested_property: Optional[str] = None,
				 default: Optional[T] = _uninitialized, default_factory: Optional[Callable[[], T]] = None,
				 can_set=True, can_get=True):
		self.use_getter = use_getter
		self.nested_property = nested_property
		self.default = default
		self.default_factory = default_factory
		self.can_set = can_set
		self.can_get = can_get
		
		self.attr_name :str = None

	def __call__(self, func: Callable[[Any, T], T]) -> Any:
		self.attr_name = "_" + func.__name__
		
		def getter(instance: Any) -> T:
			value = self._ensure_defaulted(instance)
			
			if self.use_getter:
				return func(instance)
			return value

		def setter(instance: Any, value: T) -> None:
			self._ensure_defaulted(instance)
			if not self.use_getter:
				func(instance, value)
			else:
				if self.nested_property:
					self._set_nested_property(instance, value)
				else:
					setattr(instance, self.attr_name, value)
		
		if not self.can_set:
			if not self.use_getter:
				raise ValueError("Cannot set can_set to False when use_getter is False")
			setter = None
		if not self.can_get:
			if self.use_getter:
				raise ValueError("Cannot set can_get to False when use_getter is True")
			getter = None
		return property(getter, setter)
	
	def _ensure_defaulted(self, instance: Any) -> None:
		if self.nested_property:
			value = self._get_nested_property(instance)
			if value is self._uninitialized:
				value = self._get_default(instance)
				self._set_nested_property(instance, value)
		else:
			value = getattr(instance, self.attr_name, self._uninitialized)
			if value is self._uninitialized:
				value = self._get_default(instance)
				setattr(instance, self.attr_name, value)
		return value
				
	def _safe_getattr(self, instance: Any, attr: str, path: str) -> Any:
		if not hasattr(instance, attr):
			raise AttributeError(f"Attribute resolution failed for '{attr}' in path '{path}'")
		return getattr(instance, attr, self._uninitialized)

	def _get_default(self, instance: Any) -> T:
		if self.default_factory:
			value = self.default_factory()
		elif self.default is not self._uninitialized:
			value = self.default
		else:
			value = None
		return value

	def _get_nested_property(self, instance: Any) -> T:
		current = instance
		path = ""
		for part in self.nested_property.split('.'):
			path = f"{path}.{part}" if path else part
			current = self._safe_getattr(current, part, path)
		return current

	def _set_nested_property(self, instance: Any, value: T) -> None:
		parts = self.nested_property.split('.')
		current = instance
		path = ""
		for part in parts[:-1]:
			path = f"{path}.{part}" if path else part
			current = self._safe_getattr(current, part, path)
		if not hasattr(current, parts[-1]):
			raise AttributeError(f"Attribute resolution failed for '{parts[-1]}' in path '{path}'")
		setattr(current, parts[-1], value)

if __name__ == "__main__":
	class Thing:
		def __init__(self):
			self.thing2 = Thing2()

	class Thing2:
		def __init__(self):
			self.thing = 5
			self.another = 10

	# Example usage
	class MyClass:
		def __init__(self):
			self._value = AutoProperty._uninitialized
			self.thing = Thing()

		@AutoProperty(default=10, use_getter=True)
		def value(self) -> int:
			return self._value * 2

		@AutoProperty(nested_property="thing.thing2.thing", default_factory=lambda: 5, use_getter=True)
		def nested_prop(self) -> int:
			pass

		@AutoProperty(nested_property="thing.thing2.another")
		def nested_setter(self, value: int) -> int:
			print(f"Setting nested property to {value}")
			return value + 1
		
		@AutoProperty(default_factory=Thing, use_getter=True)
		def thing2(self) -> Thing:
			pass

	mc = MyClass()
	print(mc.value)  # Uses the default value
	mc.value = 20  # Sets a new value
	print(mc.value)  # Uses the custom getter logic

	# Nested property examples
	print(mc.nested_prop)  # Uses the default_factory value
	mc.nested_prop = 25
	print(mc.nested_prop)

	# Demonstrating custom setter for a nested property
	print(mc.nested_setter)
	mc.nested_setter = 30
	print(mc.nested_setter)

	print(mc.thing.thing2.another)
	mc.thing.thing2.another = 40
	print(mc.thing.thing2.another)
	print(mc.nested_setter)
