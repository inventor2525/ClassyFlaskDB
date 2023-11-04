from ClassyFlaskDB.helpers import *

@dataclass
class FieldInfo:
	parent_class : Type[Any]
	field_name : str
	field_type : Type[Any]
	depth: int
	
@dataclass
class FieldsInfo:
		__model_class__ : Type[Any]
		__field_names__ : List[str]
		__fields_dict__ : Dict[str, field]
		__primary_key_name__ : str
		
		def iterate(self, max_depth: int=-1) -> Iterable[FieldInfo]:
			"""Iterate through __model_class__'S fields and their types in a BFS manner, up to max_depth."""
			open_list = [(self.__model_class__, 0)]
			closed_list = set()

			while open_list:
				current_cls, current_depth = open_list.pop(0)

				if current_cls in closed_list or (max_depth !=-1 and current_depth > max_depth):
					continue
				closed_list.add(current_cls)

				if hasattr(current_cls, 'FieldsInfo'):
					fields_dict = current_cls.FieldsInfo.__fields_dict__
					field_names = current_cls.FieldsInfo.__field_names__
					type_hints = get_type_hints(current_cls)

					for fname in field_names:
						if fname in fields_dict:
							field_type = fields_dict[fname].type
							field_type = resolve_type(field_type, current_cls)
						elif fname in type_hints:
							field_type = type_hints[fname]
							field_type = resolve_type(field_type, current_cls)
						else:
							attr = getattr(current_cls, fname)
							field_type = type(attr)

						# Store the current depth in the FieldInfo
						if not hasattr(field_type, 'FieldsInfo'):
							yield FieldInfo(current_cls, fname, field_type, current_depth)
						else:
							open_list.append((field_type, current_depth + 1))

	
def capture_field_info(cls:Type[Any], excluded_fields:Iterable[str]=[], included_fields:Iterable[str]=[], auto_include_fields=True, exclude_prefix:str="_") -> FieldsInfo:
	excluded_fields = chain(excluded_fields, [
		primary_key_field_name,
		inner_schema_class_name
	])
	
	field_names, fields_dict = get_fields_matching(cls, excluded_fields, included_fields, auto_include_fields, exclude_prefix)
	
	#Get the primary key name:
	primary_key_name = None
	if hasattr(cls, primary_key_field_name):
		primary_key_name = cls.__primary_key_name__
		
	for field_name in field_names:
		field = fields_dict[field_name]
		if "primary_key" in field.metadata and field.metadata["primary_key"]:
			if primary_key_name is not None:
				raise ValueError(f"Multiple primary keys specified in {cls}.")
			primary_key_name = field_name

	if primary_key_name is None:
		if 'id' in field_names:
			primary_key_name = 'id'
		else:
			raise ValueError(f"No primary key specified for {cls}.")
	
	setattr(cls, 'FieldsInfo', FieldsInfo(cls, field_names, fields_dict, primary_key_name))
	return cls