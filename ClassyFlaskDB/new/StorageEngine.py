from typing import List, Dict, Any, Union, TypeVar, Generic, Iterator, Mapping, Tuple
from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass, field
from .ClassInfo import *

T = TypeVar('T')
class StorageEngineQuery(ABC, Generic[T]):
	@abstractmethod
	def filter_by_id(self, obj_id: Any) -> T:
		...
	
	@abstractmethod
	def first(self) -> T:
		...
		
	@abstractmethod
	def all(self) -> Iterator[T]:
		...

T = TypeVar('T')

@dataclass
class StorageEngine(ABC):
	context:Dict[Type, Dict[Any, Any]] = field(default_factory=dict, kw_only=True)
	
	@abstractproperty
	def transcoders(self) -> Iterator['Transcoder']:
		...
	
	@abstractmethod
	def setup(self, data_decorator: 'DATADecorator'):
		...
	
	@abstractmethod
	def merge(self, obj: Any, persist: bool = False):
		...
	
	@abstractmethod
	def get_transcoder_type(self, type_: Type) -> Type['Transcoder']:
		...
	
	@abstractmethod
	def query(self, cls: Type[T]) -> StorageEngineQuery[T]:
		...

@dataclass
class TranscoderCollection:
	transcoders:List['Transcoder'] = field(default_factory=list)
	
	def add(self, transcoder_cls):
		self.transcoders.append(transcoder_cls)
		return transcoder_cls

from .DATADecorator import *
#imported here to avoid circular reference but fulfill the
#IDE's curiosity about those forward references above.