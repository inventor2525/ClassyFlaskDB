from functools import wraps as _wraps

def wraps(wrapped):
	'''
	Wraps a function, preserving the wrapped function's
	docstring by appending it to the new docstring.
	'''
	def decorator(f):
		original_doc = wrapped.__doc__ or ""
		new_doc = f.__doc__ or ""
		
		wrapped_f = _wraps(wrapped)(f)
		wrapped_f.__doc__ = f"{new_doc}\n{original_doc}"
		
		return wrapped_f
	return decorator

if __name__ == "__main__":
	def field(*args, **kwargs):
		"""This is field's original docstring."""
		pass

	@wraps(field)
	def custom_field(*args, **kwargs):
		"""This is custom_field's docstring."""
		pass

	print(custom_field.__doc__)