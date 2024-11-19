from typing import List, Dict, Any, Union, TypeVar, Generic, Iterator, Mapping, Tuple, Optional, ClassVar,Iterable, ForwardRef
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
	data_decorator: ForwardRef('DATADecorator')
	
	context:Dict[Type, Dict[Any, Any]] = field(default_factory=dict, kw_only=True)
	'''Used to maintain objects in memory between queries and possibly merges, by id.'''
	
	files_dir: Optional[str] = field(default=None, kw_only=True)
	'''The location that files will be stored (audio, images, etc)'''
	
	id_mapping: ClassVar[Dict[int, str]] = {}
	'''Used to store id's of objects that were not decorated with DATADecorator.'''
	
	group_names: Optional[Iterable[str]] = field(default=None,kw_only=True)
	'''When decorating a class with a DATADecorator, you can assign it an optional group name (default is 'main'), and with this you can specify which class groups you want in this storage engine. Default is that all that were decorated by the passed data decorator will be used.'''
	def __post_init__(self):
		if self.group_names:
			self.group_names = set(self.group_names)
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
	
	def setup(self):
		pass
	
	@abstractmethod
	def merge(self, obj: Any, persist: bool = False):
		...
	
	@abstractmethod
	def get_transcoder_type(self, type_: Type, field_:Optional[Field]=None) -> Type['Transcoder']:
		...
	
	@abstractmethod
	def query(self, cls: Type[T]) -> StorageEngineQuery[T]:
		...
	
	@staticmethod
	def get_id(obj:Any):
		'''
		Get's obj's primary key if it exists,
		else returns a key from id_mapping and
		creates one if there isn't one there yet.
		'''
		if obj is None:
			return None
		
		try:
			return obj.get_primary_key()
		except:
			pass
		
		try:
			return StorageEngine.id_mapping[id(obj)]
		except:
			new_id = str(uuid.uuid4())
			StorageEngine.id_mapping[id(obj)] = new_id
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
	
	def classes(self) -> Iterator[Tuple[type, ClassInfo]]:
		for cls in self.data_decorator.registry.values():
			class_info = ClassInfo.get(cls)
			if self.group_names and class_info.group_name not in self.group_names:
				# Skip any classes not in a group we're configured to use
				continue
			yield (cls, class_info)
	

@dataclass
class TranscoderCollection:
	transcoders:List['Transcoder'] = field(default_factory=list)
	
	def add(self, transcoder_cls):
		self.transcoders.append(transcoder_cls)
		return transcoder_cls

from .DATADecorator import *
#imported here to avoid circular reference but fulfill the
#IDE's curiosity about those forward references above.