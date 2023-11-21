from typing import Type, Iterable, Tuple, List, Dict, Any, Set, get_args, get_origin, ForwardRef

class TypeResolver:
	locals = {}

	@classmethod
	def append_globals(cls, global_context):
		"""Appends global context to the local context."""
		cls.locals.update(global_context)

	@classmethod
	def resolve_type(cls, type_hint, context_dict=None):
		"""Helper function to resolve string type hints and ForwardRefs."""
		# Combine self.locals with the provided context_dict
		combined_context = {**cls.locals, **(context_dict or {})}

		if isinstance(type_hint, str):
			return cls.resolve_type(eval(type_hint, globals(), combined_context), combined_context)

		if isinstance(type_hint, ForwardRef):
			return eval(type_hint.__forward_arg__, globals(), combined_context)

		# Check if type_hint is a generic type
		origin = get_origin(type_hint)
		if origin:
			args = tuple(cls.resolve_type(arg, combined_context) for arg in get_args(type_hint))
			return origin[args]

		return type_hint
	
if __name__ == '__main__':
	class bla:
		# Define ClassA as a forward reference in type hint
		class ClassB:
			bla: Tuple[List[Tuple[List[Tuple["foo","foo"]], "bla.ClassB"]], Dict[str,"bla.ClassA"]]

		class ClassA:
			pass

	class foo:
		pass
	# Getting the type hint from ClassB's 'bla' attribute and resolving it
	TypeResolver.append_globals(globals())  # Append the global context

	attr_type_hint = bla.ClassB.__annotations__['bla']
	resolved_type = TypeResolver.resolve_type(r"""Tuple["foo", "foo"]""")

	print(attr_type_hint, type(attr_type_hint))
	print(resolved_type)  # Expected: typing.Tuple[__main__.ClassA]

	def traverse_resolved_type(type_hint):
		"""Recursively traverses and prints components of a type hint."""
		
		origin = get_origin(type_hint)
		if not origin:
			# It's a base type, not a generic
			print(type_hint)
			return

		print(origin)  # E.g., 'list' or 'tuple'

		for arg in get_args(type_hint):
			traverse_resolved_type(arg)

	# Using your previously resolved type:
	traverse_resolved_type(resolved_type)