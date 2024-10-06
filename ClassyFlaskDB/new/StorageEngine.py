from typing import List, Dict, Any, Union, TypeVar, Generic, Iterator, Mapping, Tuple, Optional
from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass, field
from .ClassInfo import *
import uuid
import os

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
	files_dir: Optional[str] = field(default=None, kw_only=True)
	id_mapping: Dict[int, str] = field(default_factory=dict, kw_only=True)
	
	def __post_init__(self):
		if self.files_dir:
			if isinstance(self.files_dir, str) and len(self.files_dir) > 0:
				self.files_dir = os.path.expanduser(self.files_dir)
				try:
					os.makedirs(self.files_dir, exist_ok=True)
				except Exception as e:
					print(f"Failed to create files directory {self.files_dir}: {e}")
					self.files_dir = None
			else:
				print("Invalid files_dir provided. Setting to None.")
				self.files_dir = None
				
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
	
	def get_id(self, obj:Any):
		'''
		Get's obj's primary key if it exists,
		else returns a key from id_mapping and
		creates one if there isn't one there yet.
		'''
		try:
			return obj.get_primary_key()
		except:
			pass
		
		try:
			return self.id_mapping[id(obj)]
		except:
			new_id = str(uuid.uuid4())
			self.id_mapping[id(obj)] = new_id
			return new_id
		
	def get_binary_path(self, obj:Any) -> Optional[str]:
		'''
		Determines the path the obj would be saved at
		(if it's Transcoder would save it as a separate
		file), and returns a complete path to it, or None
		if it would not be saved as a file.
		'''
		transcoder = self.get_transcoder_type(type(obj))
		if transcoder is None:
			return None
		
		extension = transcoder.extension()
		if extension is None:
			return None
		
		id = str(self.get_id(obj))
		return os.path.join(self.files_dir, f"{id}.{extension}")

@dataclass
class TranscoderCollection:
	transcoders:List['Transcoder'] = field(default_factory=list)
	
	def add(self, transcoder_cls):
		self.transcoders.append(transcoder_cls)
		return transcoder_cls

from .DATADecorator import *
#imported here to avoid circular reference but fulfill the
#IDE's curiosity about those forward references above.