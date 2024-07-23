from ClassyFlaskDB.new.SQLStorageEngine import *
from datetime import datetime
from typing import Any, List, TypeVar
import tzlocal

def get_local_time():
	local_tz = tzlocal.get_localzone()
	return datetime.now(local_tz)

class ObjectTagsProxy():
	'''
	Maps an object's Tags into dot syntax.
	
	With this, instead of having to do:
	Obj.tags.append[Tag("my_tag", someObj)]
	Obj.tags[-1].obj == someObj
	
	you can do:
	Obj.props.my_tag = someObj
	Obj.props.my_tag == someObj
	'''
	def __init__(self, proxy_for:"Object"):
		self._proxy_for = proxy_for
		self._tags = proxy_for.tags
		self._tags_by_key = {tag.key: tag for tag in proxy_for.tags}

	def __getattribute__(self, name: str) -> Any:
		if name.startswith("_"):
			return super().__getattribute__(name)
		elif name in self._tags_by_key:
			return self._tags_by_key[name].obj
		raise AttributeError(f"Property not found on {self._proxy_for}.props", name=name, obj=self._tags)

	def __setattr__(self, name: str, value: Any) -> None:
		if name.startswith("_"):
			super().__setattr__(name, value)
		elif name in self._tags_by_key:
			self._tags_by_key[name].obj = value
		else:
			new_tag = Tag(key=name, obj=value)
			self._tags_by_key[name] = new_tag
			self._tags.append(new_tag)

DATA = DATADecorator()

T = TypeVar('T')
@DATA
@dataclass
class Object:
	date_created: datetime = field(
		default_factory=get_local_time, kw_only=True, 
		metadata={"no_update":True}
	)
	source: "Object" = field(default=None, kw_only=True)
	tags: List["Tag"] = field(default_factory=list, kw_only=True)
	
	def __post_init__(self):
		self.props = ObjectTagsProxy(self)
		
	def add_source(self:T, other:"Object") -> T:
		s = self
		while s.source:
			s = s.source
		s.source = other
		return self
	
	def create_edit(self, new:"Object") -> "EditSource":
		edit = EditSource(self, new)
		new.add_source(edit)
		return new
		
	def __or__(self:T, other:"Object") -> T:
		return self.add_source(other)
	def __and__(self, new:"Object") -> "EditSource":
		return self.create_edit(new)
	
@DATA
@dataclass
class Tag(Object):
	key: str
	obj: Object = None

@DATA
@dataclass
class EditSource(Object):
	"""Describes the source of an object as an edit of another."""
	original: Object
	new: Object
	
	def original_object(self) -> Object:
		"""
		Returns the most original object in the edit chain.
		"""
		prev = self.original
		while prev is not None and prev.source is not None:
			if isinstance(prev.source, EditSource):
				prev = prev.source.original
			else:
				break
			
		return prev
	
	def original_source(self) -> Object:
		"""
		Returns the most original object source in the edit chain.
		"""
		return self.original_object().source