from ClassyFlaskDB.DATA import *
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
	def __init__(self, proxy_for:"Object", tags: List["Tag"]):
		self._proxy_for = proxy_for
		self._tags = tags
		self._tags_by_key = {tag.key: tag for tag in tags}

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

DATA = DATADecorator(auto_decorate_as_dataclass=False)

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
		self.props = ObjectTagsProxy(self.tags)
		
	def __or__(self:T, other:"Object") -> T:
		s = self
		while s.source:
			s = s.source
		s.source = other
		return self

@DATA
@dataclass
class Tag(Object):
	key: str
	obj: Object = None