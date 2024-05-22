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
	primary_key_name : str = None
	_type_hints : Dict[str, Type[Any]] = field(init=False, repr=False, default_factory=dict)
	no_update_fields : List[str] = field(default_factory=list) #names of fields that have no_update=True in metadata
	
	@property
	def type_hints(self) -> Dict[str, Type[Any]]:
		if self._type_hints is None:
			self._type_hints = get_type_hints(self.model_class)
		return self._type_hints
	
	def get_field_type(self, field_name:str) -> Type[Any]:
		if not hasattr(self, "_field_types"):
			self._field_types = {}
			
		field_type = self._field_types.get(field_name, None)
		if field_type:
			return field_type
		
		# Get field type:
		if field_name in self.fields_dict:
			field_type = self.fields_dict[field_name].type
			field_type = TypeResolver.resolve_type(field_type)
		elif field_name in self.type_hints:
			field_type = self.type_hints[field_name]
			field_type = TypeResolver.resolve_type(field_type)
		else:
			attr = getattr(self.model_class, field_name)
			if isinstance(attr, property):
				field_type = extract_property_type(self.model_class, field_name)
			else:
				field_type = type(attr)
		self._field_types[field_name] = field_type
		return field_type
	
	def _gen_fields_with(self):
		self._fields_with_FieldsInfo = []
		self._list_fields_with_FieldsInfo = []
		for field_name in self.field_names:
			field_type = self.get_field_type(field_name)
			if hasattr(field_type, "FieldsInfo"):
				self._fields_with_FieldsInfo.append(field_name)
			elif hasattr(field_type, "__origin__") and field_type.__origin__ in [list, tuple, set]:
				self._list_fields_with_FieldsInfo.append(field_name)
	
	@property
	def fields_with_FieldsInfo(self) -> List[str]:
		if hasattr(self, "_fields_with_FieldsInfo"):
			return self._fields_with_FieldsInfo
		
		self._gen_fields_with()
		return self._fields_with_FieldsInfo
	
	@property
	def list_fields_with_FieldsInfo(self) -> List[str]:
		if hasattr(self, "_list_fields_with_FieldsInfo"):
			return self._list_fields_with_FieldsInfo
		
		self._gen_fields_with()
		return self._list_fields_with_FieldsInfo
	
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
		"__primary_key_name__",
		"FieldsInfo"
	])
	
	field_names, fields_dict = get_fields_matching(cls, excluded_fields, included_fields, auto_include_fields, exclude_prefix)
	fi = FieldsInfo(cls, field_names, fields_dict)
	
	#Get the primary key name:
	if hasattr(cls, "__primary_key_name__"):
		fi.primary_key_name = cls.__primary_key_name__
		if fi.primary_key_name not in field_names:
			field_names.append(fi.primary_key_name)
		
	for field_name in fields_dict:
		field = fields_dict[field_name]
		if "primary_key" in field.metadata and field.metadata["primary_key"]:
			if fi.primary_key_name is not None:
				raise ValueError(f"Multiple primary keys specified in {cls}.")
			fi.primary_key_name = field_name
		if field.metadata.get("no_update",False):
			fi.no_update_fields.append(field_name)

	if fi.primary_key_name is None:
		if 'id' in field_names:
			fi.primary_key_name = 'id'
	
	setattr(cls, 'FieldsInfo', fi)
	return cls