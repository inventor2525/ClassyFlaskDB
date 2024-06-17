from .ClassInfo import *
from ClassyFlaskDB.DATA.ID_Type import ID_Type
from typing import TypeVar, Type, Protocol, Any
from dataclasses import dataclass, Field
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
				f = Field(default_factory=new_id)
				f.name = classInfo.primary_key_name
				f.type = str
				classInfo.fields[f.name] = f
			
			if self.id_type == ID_Type.UUID:
				def new_id(self):
					self.auto_id = str(uuid.uuid4())
				add_id(classInfo, new_id)
			elif self.id_type == ID_Type.HASHID:
				def new_id(self):
					pass
				add_id(classInfo, new_id)
			else:
				raise ValueError(f"A primary_key_name was not supplied for {classInfo.cls} yet it is set to {ID_Type.USER_SUPPLIED}. You must have a field with 'primary_key':True in it's metadata or define __primary_key_name__ in the class's definition. In here: ({classInfo.cls})")
			
			init = cls.__init__
			def __init__(self, *args, **kwargs):
				init(self, *args, **kwargs)
				self.new_id()
			setattr(cls, "__init__", __init__)
		setattr(cls, "get_primary_key", __init__)
		return cls