from ClassyFlaskDB.DATA.ID_Type import ID_Type
from .ClassInfo import *
from .Transcoder import *
from .StorageEngine import *
from .AutoID import *

@dataclass
class DATADecorator(InfoDecorator):
	storageEngine:StorageEngine
	
	@overload
	def __call__(self, cls:Type[T]) -> Union[Type[T], 'AutoID.Interface']:
		pass
	@overload
	def __call__(self, included_fields: Iterable[str] = [], excluded_fields: Iterable[str] = [], id_type:ID_Type=ID_Type.UUID, hashed_fields:List[str]=None) -> Callable[[Type[T]], Union[Type[T], Type[AutoID.Interface]]]:
		pass
	def __call__(self, *args, **kwargs):
		return super().__call__(*args, **kwargs)

	def decorate(self, cls: Type[T], included_fields: Iterable[str] = [], excluded_fields: Iterable[str]=[], id_type:ID_Type=ID_Type.UUID, hashed_fields:List[str]=None) -> Union[Type[T], Type[AutoID.Interface]]:
		cls = super().decorate(cls, included_fields, excluded_fields)
		classInfo = ClassInfo.get(cls)
		
		cls = AutoID(id_type)(cls)
		
		old_getattr = cls.__getattr__
		old_setattr = cls.__setattr__
		no_default = object()
		
		transcoders_name = "__transcoders__"
		def get_transcoder(obj_self, name, default=no_default):
			objs_transcoders = getattr(obj_self, transcoders_name, {})
			if len(objs_transcoders)==0:
				setattr(obj_self, transcoders_name, objs_transcoders)
			if name in objs_transcoders:
				return objs_transcoders[name]
			
			transcoder = Transcoder.get_transcoder(self.storageEngine.transcoders, classInfo, classInfo.fields[name])
			if default is not no_default:
				transcoder.set(default)
			objs_transcoders[name] = transcoder
			return transcoder
			
		def getattr(self, name:str, default=no_default):
			if name in classInfo.field_names:
				transcoder = get_transcoder(self, name, default)
				return transcoder.get()
			if default is no_default:
				return old_getattr(self, name)
			else:
				return old_getattr(self, name, default)
		def setattr(self, name:str, value):
			if name in classInfo.field_names:
				transcoder = get_transcoder(self, name)
				transcoder.set(value)
			else:
				old_setattr(self, name, value)
				
		setattr(cls, "__getattr__", getattr)
		setattr(cls, "__setattr__", setattr)