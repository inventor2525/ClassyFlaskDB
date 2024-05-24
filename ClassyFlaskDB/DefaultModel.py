from ClassyFlaskDB.DATA import *
from datetime import datetime
from typing import List
import tzlocal

def get_local_time():
	local_tz = tzlocal.get_localzone()
	return datetime.now(local_tz)

DATA = DATADecorator(auto_decorate_as_dataclass=False)

@DATA
@dataclass
class Object:
	date_created: datetime = field(
		default_factory=get_local_time, kw_only=True, 
		metadata={"no_update":True}
	)
	source: "Object" = field(default=None, kw_only=True)
	tags: List["Tag"] = field(default_factory=list, kw_only=True)

	def __or__(self, other):
		if hasattr(self, 'source'):
			self.source = other
		else:
			self.source = other
		if other.source is not None:
			other.source | other
		return other
	
@DATA
@dataclass
class Tag(Object):
	key: str
	
@DATA
@dataclass
class Source(Object):
	pass