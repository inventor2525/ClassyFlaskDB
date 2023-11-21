import inspect
from typing import Any, get_type_hints

def extract_property_type(cls: Any, property_name: str) -> Any:
	"""
	Extracts the return type hint of the getter method of a property in a class.
	"""
	if property_name in cls.__dict__:
		prop = getattr(cls, property_name)
		if isinstance(prop, property):
			getter = prop.fget
			if getter is not None:
				hints = get_type_hints(getter)
				return hints.get('return')
	return None

# Example usage
class Example:
	@property
	def my_property(self) -> str:
		return "example"

# Extracting the type hint
property_type = extract_property_type(Example, 'my_property')
print(property_type)  # Output will be <class 'str'>
