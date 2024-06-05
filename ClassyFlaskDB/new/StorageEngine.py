from .Transcoder import *
from .ClassInfo import *
from abc import ABC, abstractmethod
from typing import Dict, Any, Type, TypeVar, Iterator, Generic, List, overload
from dataclasses import dataclass, field as field_factory

T = TypeVar('T')
class StorageEngineQuery(ABC, Generic[T]): #TODO, somehow generically include with StorageEngine so a StorageEngine sub class has to define a StorageEngineQuery to use. Also somehow include T in StorageEngineQuery as a generic. Essentially I'm re-building a thin orm here, so... look at sql alchamy's for reference
	@abstractmethod
	def all(self) -> Iterator[T]:
		pass
	
	@abstractmethod
	def id(self, id:Any) -> T:
		'''Returns a single queried object where query.id == id'''
		pass

T = TypeVar('T', Transcoder)
@dataclass
class StorageEngine(ABC):
	transcoders:List[Type[Transcoder]] = field_factory(default_factory=list, kw_only=True)
	
	def add(self, transcoder:Type[T]) -> Type[T]: #TODO:  + priority
		'''
		Decorator you can use to keep track of which
		transcoders can be used with this type of StorageEngine.
		'''
		self.transcoders.append(transcoder)
		return transcoder
	
	def get_transcoder(self, classInfo:ClassInfo, field:Field) -> Transcoder:
		for transcoder in self.transcoders:
			if transcoder.validate(classInfo, field):
				return transcoder(field)
		raise ValueError(f"There is no suitable transcoder type provided for {classInfo.qualname}.{field.name} ({field.type})")
	
	def setup(self, registry:Dict[str, type]):
		for cls in registry.values():
			classInfo = ClassInfo.get(cls)
			for field in classInfo.fields.values(): #TODO: not needed since we get lazilly in getattr and setattr
				transcoder = self.get_transcoder(classInfo, field)
	@abstractmethod
	def merge(self, obj:Any):
		pass
	
	@abstractmethod
	def query(self, obj_type:TypeVar[T]) -> StorageEngineQuery[T]:
		pass