from .StorageEngine import *
from .DATADecorator import *

@dataclass
class JSON_Engine(StorageEngine):
	def merge(self, obj:Any):
		classInfo = ClassInfo.get(obj)
		if classInfo is None:
			raise ValueError(f"{obj} must be a type that has a ClassInfo assigned to it.")

jEngine = JSON_Engine()

@jEngine.add
@dataclass
class BasicsTranscoder(Transcoder):
	valid_types = {
		int,
		float,
		str,
		bool
	}
	
	def validate(cls, classInfo:ClassInfo, field:Field) -> bool:
		return field.type in cls.valid_types

@jEngine.add
@dataclass
class ObjectTranscoder(Transcoder):
	def validate(cls, classInfo:ClassInfo, field:Field) -> bool:
		return ClassInfo.has_ClassInfo(classInfo.cls)
	
	def setup(cls, classInfo:ClassInfo, field:Field):
		pass
	
	def encode(cls, value:DATADecorator.Interface) -> Any:
		return value.get_primary_key()
	
	def decode(cls, encoded:T) -> T:
		return encoded
	
	def get_hashing_value(cls, value:DATADecorator.Interface) -> Any:
		return value.get_primary_key()