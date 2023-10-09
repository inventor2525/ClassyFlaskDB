from typing import Type, Iterable, Tuple, Dict, Any, Set
from dataclasses import field, is_dataclass, dataclass, fields
from itertools import chain

def get_fields_matching(
		cls:Type[Any], 
		excluded_fields:Iterable[str]=[], included_fields:Iterable[str]=[],
		auto_include_fields=True, exclude_prefix:str="_"
	) -> Tuple[Set[str], Dict[str, field]]:
	
	inclusion_set = set(included_fields)
	exclusion_set = set(excluded_fields)
	
	fields_dict = {}
	if is_dataclass(cls):
		fields_dict = {f.name: f for f in fields(cls)}
		
		# Get any fields that have information about what we might
		# want to do with them in sql in in their metadata
		def handle_should_save(field):
			'''
			Adds the field to the exclusion or inclusion set based on if metadata
			contains should_save and returns whether or not it did contain should_save.
			'''
			if "should_save" in field.metadata:
				if not field.metadata["should_save"]:
					exclusion_set.add(field.name)
				else:
					inclusion_set.add(field.name)
				return True
			return False
			
		for field in fields_dict.values():
			if "internal" in field.metadata:
				if not handle_should_save(field):
					exclusion_set.add(field.name)
			else:
				if not handle_should_save(field):
					if auto_include_fields:
						inclusion_set.add(field.name)	
								
	def safe_starts_with(s:str, prefix:str):
		if prefix is None or len(prefix)==0:
			return False
		return s.startswith(prefix)
		
	field_names = set((attr for attr in chain(
		inclusion_set, 
		(
			attr for attr in dir(cls) if 
			not callable(getattr(cls, attr)) 
			and not safe_starts_with(attr, exclude_prefix)
		) if auto_include_fields else []
	) if attr not in exclusion_set))
	
	#Order field_names in the order they were defined in cls
	field_names = sorted(field_names, key=lambda x: list(cls.__annotations__).index(x) if x in cls.__annotations__ else float('inf'))
	return field_names, fields_dict