from copy import deepcopy

def method_decorator(model_attr_name):
	'''
	Decorator that creates a class that can be used as a decorator for
	methods that will add a instance of the class to the method as an attribute.
	'''
	def decorator(cls):
		def __call__(self, func):
			setattr(func, model_attr_name, self)
			return func

		setattr(cls, '__call__', __call__)
		return cls
	return decorator

if __name__ == '__main__':
	from dataclasses import dataclass

	@dataclass
	@method_decorator('__route__')
	class Route:
		name: str

	class Faux:
		@Route("ExampleModel")
		def bar(self):
			if hasattr(self.bar, '__route__'):
				model = self.bar.__route__
				print(f"Using model: {model.name}")
			return "Method logic here"
	
	# Testing the decorated method
	faux_instance = Faux()
	print(faux_instance.bar())  # This will print the model info