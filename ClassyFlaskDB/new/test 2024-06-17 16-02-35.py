# from ClassyFlaskDB.new.DATADecorator import *
from typing import List, Dict
from datetime import datetime
from dataclasses import dataclass
from ClassyFlaskDB.new.InfoDecorator import *
from ClassyFlaskDB.new.AutoID import *
DATA = InfoDecorator()

@DATA
@dataclass
class Foo():
	bar1:int
	bar2:float

@DATA
@dataclass
class MyObj():
	name : str
	date : datetime
	my_list : List[str]
	my_dict : Dict[str, Foo]
	
	def __post_init__(self):
		print("Hello post init")


mo = MyObj("test", datetime.now(), ["hi", "computer"], {"o1":Foo(1,3.14), "o2":Foo(2,6.28)})

mo2 = object.__new__(MyObj)
mo2.name = mo.name
mo2.date = mo.date
mo2.my_list = mo.my_list
mo2.my_dict = mo.my_dict
print("set vars")
if hasattr(MyObj, "__post_init__"):
	mo2.__post_init__()

print(mo)
print(mo2)
print("hello world")

@dataclass
class DirtyInterface: #IDEA: this dirty interface makes me wonder if things like it and auto idea can be read from and applied to a class automatically like a patch class
	_dirty:bool
	def _is_dirty(self, isDirt:Dict[int, bool]) -> bool:
		#this has to be implemented by the type, list, dict, obj, etc to check all elements
		
		#if a type could some how have a dirty able applied to it like a decorator, the list could create this function based on if it's elements are of a type that has a dirtyable
		
		#this should call is_dirty on each element 
		pass
	
	def is_dirty(self, isDirt:Dict[int, bool]) -> bool:
		if self._dirty:
			return True
		if id(self) in isDirt:
			return isDirt[id(self)]
		dirty = self._is_dirty(isDirt)
		isDirt[id(self)] = dirty
		return dirty
	
		#notes from before:
		#the dict is a map from obj's id to if it is dirty.
		#
		#it's here so we only have to check into a object and it's children 1 time
		
	def clear_dirty(self, isDirt:Dict[int, bool]) -> Any:
		self._dirty = False
		isDirt[id(self)]=False
		
		#notes from before:
		#iterate all fields that are 'dirtiable' (objs, lists, dicts) and set them not dirty
		#dirty will only be tracked for this object's storage engine
		#
		# do we need the isDirt here? think through this as we iterate something with circular refs


@dataclass
class Transcoder:
	can_merge:bool #TODO: better way to do this
	
	def validate(cls, classInfo:ClassInfo, field:Field) -> bool:
		'''
		Returns true if this Transcoder type can be used with this Field.
		'''
		return False
	
	def encode(self, name:str, value:Any):
		pass
	def decode():
		pass
	
	@classmethod
	def for_type(obj:type) -> "Transcoder":
		pass
	def _merge(context, obj:DirtyInterface, is_dirty:dict, parent=None):
		pass
	def merge(context, obj:DirtyInterface, is_dirty:dict, parent=None):
		if obj.is_dirty(is_dirty):
			self._merge(obj, is_dirty, parent)
			obj.clear_dirty(is_dirty)
		
@dataclass
class objects_new_methods(AutoID.Interface, MyObj, DirtyInterface):
	original_has_attr : Callable[[str], bool]
	original_get_attr : Callable[[str], Any]
	original_set_attr : Callable[[str, Any], None]   #TODO: look into how getattr and setattr can be overriden. Can we have a child object like sql alchemy with all these things in it rather than poluting the main object, and could it have the origional getters or setters..... and does object.setattr act as a viable replacement to tracking the origionals manually or does it simply call our overrides
	__transcoders__:Dict[str, "Transcoder"]
	# __un_loaded__:Set[str]
	
	def __post_load__(self):
		self._dirty = False
		# self.__un_loaded__ = set(self.__class_info__.fields.keys())
		#TODO: ensure fields setup that aren't part of __class_info__.fields -- the logic for this is written, (in data decorator?)
		if self.original_has_attr("__post_init__"):
			self.__post_init__()
	
	def has_attr(self, name:str) -> bool:
		return self.original_has_attr(name) or (name in self.__class_info__.fields)
	
	def _is_loaded(self, name:str) -> bool:
		pass #TODO: determine this somehow. use '__un_loaded__' maybe? idk
	def get_attr(self, name:str) -> Any:
		if name not in self.__class_info__.fields or self._is_loaded(name):
			pass
		else:#load
			pass
		
	def set_attr(self, name:str, value:Any):
		old_value = self.original_get_attr(name)
		if old_value is not value:
			self._dirty = True
		# what do with list dict ... need override methods
			#it needs to be 'instrumented'. Dirty tracking and custom get set.
			#this is what I wonder if can happen in the transcoder instance
		self.original_set_attr(name, value)

class DateTimeTranscoder(Transcoder):
	can_merge = False
	pass

class ObjTranscoder(Transcoder):
	def _merge(context, obj:objects_new_methods, parent=None):
		encodeds = {}
		for f in obj.__class_info__.fields.values():
			transcoder = obj.__transcoders__[f.name]
			if transcoder.can_merge:
				transcoder.merge(obj, is_dirty, parent) #in json, this 'parent' would be what we are assigning the value into, in sql what.... ? (brain farting as typing this)
			encodeds[f.name] = transcoder.encode()
		
		#TODO: engine specific merge logic

@dataclass
class ListTranscoder(Transcoder):
	value_transcoder:Transcoder
	def merge(context, obj:list, parent:objects_new_methods):
		#IDEA! : use the parent to store some things , like is dirty for the list or serialized values
		
	def qeury():
		#return a hacked list thing?
		
T = TypeVar('T')
class storage_engine():
	context: dict #something to store what has been loaded
	
	def get_transcoder_type(self, classInfo:ClassInfo, field:Field) -> Type[Transcoder]:
		for transcoder_type in self.transcoder_types:
			if transcoder_type.validate(classInfo, field):
				return transcoder_type
		raise ValueError(f"There is no suitable transcoder type provided for {classInfo.qualname}.{field.name} ({field.type})")
	
	def get_transcoder(self, classInfo:ClassInfo, field:Field) -> Transcoder:
		transcoder_type = self.get_transcoder_type(classInfo, field)
		return transcoder_type(self.context, classInfo, field)
	
	def setup(self, registry:Dict[str, type]):
		for cls in registry.values():
			classInfo = ClassInfo.get(cls)
			for field in classInfo.fields.values():
				transcoder_type = self.get_transcoder_type(classInfo, field)
				transcoder_type.setup(classInfo, field)
				
	def merge(self, obj:objects_new_methods):
		t = Transcoder.for_type(type(obj))
		t.merge(self.context, obj, {})
	
	def query(self, obj_type:Type[T], obj_id:Any) -> T:
		if obj_id in self.context[obj_type]:
			return self.context[obj_type][obj_id]
		
		t = Transcoder.for_type(obj_type)
		