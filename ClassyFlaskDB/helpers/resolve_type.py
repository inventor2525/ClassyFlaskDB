from typing import Type, Iterable, Tuple, List, Dict, Any, Set, get_args, get_origin, ForwardRef

def resolve_type(type_hint, context_dict):
    """Helper function to resolve string type hints and ForwardRefs."""
    
    if isinstance(type_hint, str):
        return resolve_type(eval(type_hint, globals(), context_dict), context_dict)
		
    if isinstance(type_hint, ForwardRef):
        return eval(type_hint.__forward_arg__, globals(), context_dict)
    
    # Check if type_hint is a generic type
    origin = get_origin(type_hint)
    if origin:
        args = tuple(resolve_type(arg, context_dict) for arg in get_args(type_hint))
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
	attr_type_hint = bla.ClassB.__annotations__['bla']
	resolved_type = resolve_type(r"""Tuple["foo","foo"]""", globals())

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