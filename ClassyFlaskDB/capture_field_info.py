from ClassyFlaskDB.helpers import *

@dataclass
class FieldInfo:
	parent_type : Type[Any]
	field_name : str
	field_type : Type[Any]
	depth: int

	is_primary_key : bool = False
	is_dataclass : bool = False

	dont_go_deeper : bool = False
	stop_iterating_cls : int = 0

def get_type_hints(cls:Type[Any]) -> Dict[str, Type[Any]]:
	type_hints = {}
	for base in reversed(cls.__mro__):
		type_hints.update(getattr(base, '__annotations__', {}))
	return type_hints
@dataclass
class FieldsInfo:
	model_class : Type[Any]
	field_names : List[str]
	fields_dict : Dict[str, field]
	primary_key_name : str
	_type_hints : Dict[str, Type[Any]] = field(init=False, repr=False, default_factory=dict)

	@property
	def type_hints(self) -> Dict[str, Type[Any]]:
		if self._type_hints is None:
			self._type_hints = get_type_hints(self.model_class)
		return self._type_hints
	
	def get_field_type(self, field_name:str) -> Type[Any]:
		# Get field type:
		if field_name in self.fields_dict:
			field_type = self.fields_dict[field_name].type
			field_type = resolve_type(field_type, self.model_class)
		elif field_name in self.type_hints:
			field_type = self.type_hints[field_name]
			field_type = resolve_type(field_type, self.model_class)
		else:
			attr = getattr(self.model_class, field_name)
			field_type = type(attr)
		return field_type
	
	def iterate(self, max_depth: int=-1) -> Iterable[FieldInfo]:
		"""Iterate through __model_class__'S fields and their types in a BFS manner, up to max_depth."""
		open_list = [(self.model_class, 0)]
		closed_list = set()

		while open_list:
			current_cls, current_depth = open_list.pop(0)

			if (max_depth !=-1 and current_depth > max_depth) or current_cls in closed_list:
				continue

			if hasattr(current_cls, 'FieldsInfo'):
				fields_dict = current_cls.FieldsInfo.fields_dict
				field_names = current_cls.FieldsInfo.field_names

				# Iterate through fields in current_cls:
				for field_name in field_names:
					field_type = current_cls.FieldsInfo.get_field_type(field_name)

					# yield:
					fi = FieldInfo(current_cls, field_name, field_type, current_depth)
					if current_cls.FieldsInfo.primary_key_name == field_name:
						fi.is_primary_key = True
					if hasattr(field_type, 'FieldsInfo'):
						fi.is_dataclass = True
					yield fi

					# Handle yield return values (these control the iteration):
					if fi.is_dataclass and not fi.dont_go_deeper:
						open_list.append((field_type, current_depth + 1))
					if fi.stop_iterating_cls > 0:
						if fi.stop_iterating_cls > 1:
							closed_list.add(current_cls)
						break
	
	def iterate_cls(self, max_depth: int=-1) -> Iterable[FieldInfo]:
		closed_list = set()

		for fi in self.iterate(max_depth):
			if fi.parent_type not in closed_list:
				yield fi
				closed_list.add(fi.parent_type)
			fi.dont_go_deeper = True
			fi.stop_iterating_cls = 2

def capture_field_info(cls:Type[Any], excluded_fields:Iterable[str]=[], included_fields:Iterable[str]=[], auto_include_fields=True, exclude_prefix:str="_") -> FieldsInfo:
	excluded_fields = chain(excluded_fields, [
		"__primary_key_name__"
	])
	
	field_names, fields_dict = get_fields_matching(cls, excluded_fields, included_fields, auto_include_fields, exclude_prefix)
	
	#Get the primary key name:
	primary_key_name = None
	if hasattr(cls, "__primary_key_name__"):
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