from typing import List, Dict, Any, Union, TypeVar, Generic, Iterator, Mapping, Tuple
from .Transcoder import *
from .ClassInfo import *

T = TypeVar('T')
class StorageEngineQuery(ABC, Generic[T]): #TODO, somehow generically include with StorageEngine so a StorageEngine sub class has to define a StorageEngineQuery to use. Also somehow include T in StorageEngineQuery as a generic. Essentially I'm re-building a thin orm here, so... look at sql alchamy's for reference
	@abstractmethod
	def all(self) -> Iterator[T]:
		pass
	
	@abstractmethod
	def id(self, id:Any) -> T:
		'''Returns a single queried object where query.id == id'''
		pass

T = TypeVar('T', bound=Transcoder)
U = TypeVar('U')

@dataclass
class StorageEngine(ABC):
	transcoder_types:List[Type[Transcoder]] = field(default_factory=list, kw_only=True)
	context:Dict[Type, Dict[Any, Any]] = field(default_factory=dict, kw_only=True)
	
	def add(self, transcoder:Type[T]) -> Type[T]: #TODO:  + priority
		'''
		Decorator you can use to keep track of which
		transcoders can be used with this type of StorageEngine.
		'''
		self.transcoder_types.append(transcoder)
		return transcoder
	
	# def get_transcoder_type(self, classInfo:ClassInfo, field:Field) -> Type[Transcoder]:
	# 	for transcoder_type in self.transcoder_types:
	# 		if transcoder_type.validate(classInfo, field):
	# 			return transcoder_type
	# 	raise ValueError(f"There is no suitable transcoder type provided for {classInfo.qualname}.{field.name} ({field.type})")
	
	# def get_transcoder(self, classInfo:ClassInfo, field:Field) -> Transcoder:
	# 	transcoder_type = self.get_transcoder_type(classInfo, field)
	# 	return transcoder_type(self.context, classInfo, field)
		
	# def setup(self, registry:Dict[str, type]):
	# 	for cls in registry.values():
	# 		classInfo = ClassInfo.get(cls)
	# 		for field in classInfo.fields.values():
	# 			transcoder_type = self.get_transcoder_type(classInfo, field)
	# 			transcoder_type.setup(classInfo, field)
	
	@abstractmethod
	def merge(self, obj:Any):
		pass
	
	@abstractmethod
	def query(self, obj_type:Type[U]) -> StorageEngineQuery[U]:
		pass

class TranscoderCollection:
    def __init__(self):
        self.transcoders = []

    def add(self, transcoder_cls):
        self.transcoders.append(transcoder_cls)
        return transcoder_cls