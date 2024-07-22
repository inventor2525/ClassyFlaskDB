from .ClassInfo import *
from ClassyFlaskDB.DATA.ID_Type import ID_Type
from typing import TypeVar, Type, Protocol, Any, get_origin, get_args
from dataclasses import dataclass, Field, MISSING
from enum import Enum
from datetime import datetime
import hashlib
import uuid

T = TypeVar('T')
@dataclass
class AutoID:
	'''
	A class decorator that populates an automatically generated ID field
	and new_id method given a specified id type, if it wasn't user supplied.
	
	This also modifies the init to create an initial id.
	'''
	id_type:ID_Type
	_hash_functions = {}
	_hash_function_list = []
	
	class Interface(ClassInfo.Interface):
		auto_id:str
		def new_id(self):
			pass
		def get_primary_key(self) -> Any:
			pass
			
	def __call__(self, cls:Type[T]) -> Union[Type[T], Type['AutoID.Interface']]:
		'''
		This method returns cls with a auto_id and new_id method added to it
		so long as id_type is hash or uuid.
		
		cls's type and the return type are always the same, but the Union
		in the return type hint allows us to get auto complete for the added
		members. This may break any meta programming done with it's output,
		but is usually nicer to work with and is something while waiting for
		the typing.Intersection pep.
		'''
		classInfo = ClassInfo.get(cls)
		if classInfo.primary_key_name:
			setattr(classInfo.cls, "new_id", lambda self:...)
		else:
			def add_id(classInfo:ClassInfo, new_id:Callable[[],None]):
				classInfo.primary_key_name = "auto_id"
				setattr(classInfo.cls, "new_id", new_id)
				setattr(classInfo.cls, classInfo.primary_key_name, None)
				classInfo.cls.__annotations__[classInfo.primary_key_name] = str
				f = Field(default=MISSING, default_factory=new_id, init=True, repr=True, hash=None, compare=True, metadata=None, kw_only=MISSING)
				f.name = classInfo.primary_key_name
				f.type = str
				classInfo.fields[f.name] = f
			
			if self.id_type == ID_Type.UUID:
				def new_id(self):
					self.auto_id = str(uuid.uuid4())
				add_id(classInfo, new_id)
			elif self.id_type == ID_Type.HASHID:
				def new_id(self, deep: bool = False):
					fields = []
					for field_name, field_info in classInfo.fields.items():
						if field_name != classInfo.primary_key_name:
							value = getattr(self, field_name)
							hash_func = AutoID.get_hash_function(field_info.type)
							fields.extend(hash_func(value, field_info.type, deep))
					self.auto_id = hashlib.sha256(",".join(map(str, fields)).encode("utf-8")).hexdigest()
				add_id(classInfo, new_id)
			else:
				raise ValueError(f"A primary_key_name was not supplied for {classInfo.cls} yet it is set to {ID_Type.USER_SUPPLIED}. You must have a field with 'primary_key':True in it's metadata or define __primary_key_name__ in the class's definition. In here: ({classInfo.cls})")
			
			init = cls.__init__
			def __init__(self, *args, **kwargs):
				init(self, *args, **kwargs)
				self.new_id()
			setattr(cls, "__init__", __init__)
		def get_primary_key(self):
			return getattr(self, self.__class_info__.primary_key_name)
		setattr(cls, "get_primary_key", get_primary_key)
		return cls

	@classmethod
	def hash_function(cls, types: Union[Type, List[Type]] = None):
		def decorator(func):
			if types:
				type_list = [types] if isinstance(types, type) else types
				for t in type_list:
					cls._hash_functions[t] = func
				def validate_error(func):
					raise SyntaxError("Validate should not be used when types is passed.")
				func.validate = validate_error
				func.type_list = type_list
			else:
				def validator(validate_func):
					func.validate = validate_func
					return func
				
				func.validate = validator
			cls._hash_function_list.append(func)
			return func
		return decorator

	@classmethod
	def get_hash_function(cls, type_: Type) -> Callable:
		if type_ in cls._hash_functions:
			return cls._hash_functions[type_]
		
		for func in reversed(cls._hash_function_list):
			try:
				type_list = getattr(func, 'type_list', None)
				if type_list:
					for t in type_list:
						if issubclass(type_, t):
							cls._hash_functions[type_] = func
							return func
				elif func.validate(type_):
					cls._hash_functions[type_] = func
					return func
			except:
				pass
		
		raise ValueError(f"No suitable hash function found for {type_}")

# Hash function definitions
@AutoID.hash_function([int, float, str, bool])
def basic_hash(value: Union[int, float, str, bool], type_: Type, deep: bool) -> List[Union[str, int, float]]:
    return [value]

@AutoID.hash_function(datetime)
def datetime_hash(value: datetime, type_: Type, deep: bool) -> List[str]:
    return [value.isoformat()]

@AutoID.hash_function(Enum)
def enum_hash(value: Enum, type_: Type, deep: bool) -> List[str]:
    return [value.name]

@AutoID.hash_function()
def object_hash(value: Any, type_: Type, deep: bool) -> List[str]:
    class_info = ClassInfo.get(type(value))
    if deep and class_info.id_type == ID_Type.HASHID:
        value.new_id(deep=True)
    return [value.get_primary_key()]

@object_hash.validate
def validate_object(type_: Type) -> bool:
    return ClassInfo.has_ClassInfo(type_)

@AutoID.hash_function()
def list_hash(value: List[Any], type_: Type, deep: bool) -> List[Any]:
    h = []
    value_type = get_args(type_)[0]
    hash_func = AutoID.get_hash_function(value_type)
    for item in value:
        h.extend(hash_func(item, value_type, deep))
    return h

@list_hash.validate
def validate_list(type_: Type) -> bool:
    return get_origin(type_) is list

@AutoID.hash_function()
def dict_hash(value: Dict[Any, Any], type_: Type, deep: bool) -> List[Any]:
    h = []
    key_type, value_type = get_args(type_)
    key_hash_func = AutoID.get_hash_function(key_type)
    value_hash_func = AutoID.get_hash_function(value_type)
    for k, v in value.items():
        h.extend(key_hash_func(k, key_type, deep))
        h.extend(value_hash_func(v, value_type, deep))
    return h

@dict_hash.validate
def validate_dict(type_: Type) -> bool:
    return get_origin(type_) is dict

@AutoID.hash_function()
def set_hash(value: Set[Any], type_: Type, deep: bool) -> List[Any]:
    h = []
    value_type = get_args(type_)[0]
    hash_func = AutoID.get_hash_function(value_type)
    for item in sorted(value):  # Sort to ensure consistent hashing
        h.extend(hash_func(item, value_type, deep))
    return h

@set_hash.validate
def validate_set(type_: Type) -> bool:
    return get_origin(type_) is set