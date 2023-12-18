from ClassyFlaskDB.helpers.Decorators.AnyParam import AnyParam
from typing import Any, Callable, Type

class MethodDecorator(AnyParam):
	def decorate(self, cls:Type[Any], model_attr_name:str) -> Type[Any]:
		class InternalDecorator(AnyParam):
			def decorate(self, method:Callable, *args, **kwargs) -> Callable:
				instance = cls(*args, **kwargs)
				setattr(method, model_attr_name, instance)
				return method
		return InternalDecorator

MethodDecorator = MethodDecorator()

if __name__ == "__main__":
	# Example usage:
	
	# Apply MethodDecorator to Route class
	@MethodDecorator("__route__")
	class Route:
		def __init__(self, name=''):
			self.name = name
	Route = Route()
	
	class Faux:
		@Route("ExampleModel")
		def bar(self):
			if hasattr(self.bar, '__route__'):
				model = self.bar.__route__
				print(f"Using model: {model.name}")
			return "bar Method logic here"

		@Route
		def bla(self):
			if hasattr(self.bla, '__route__'):
				model = self.bla.__route__
				print(f"Using model: {model.name}")
			return "bla Method logic here"

	# Testing the decorated methods
	faux_instance = Faux()
	print(faux_instance.bar())  # Should print model info and "Method logic here"
	print("")
	print(faux_instance.bla())  # Should print model info and "Method logic here"
