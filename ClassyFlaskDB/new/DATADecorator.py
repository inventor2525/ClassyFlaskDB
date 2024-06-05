from ClassyFlaskDB.DATA.ID_Type import ID_Type
from .InfoDecorator import *
from .Transcoder import *
from .StorageEngine import *
from .AutoID import *

@dataclass
class DATADecorator(InfoDecorator):
	'''
	A class decorator that replaces all specified fields with 'Transcoder'
	instances that facilitate (optionally lazy) loading of objects from
	the passed generic storage engine.
	
	This also applies, to each decorated class, a ClassInfo and auto ID.
	
	Note: Remember to call finalize after every decorated class is imported!
	'''
	storageEngine:StorageEngine
	
	class Interface(AutoID.Interface):
		__transcoders__:List[Transcoder]
		'''These are only those that have had their fields 'poked' so far. Use __get_transcoder__ if you want to do some digging.'''
		def __get_transcoder__(self, name:str, default=object()) -> Transcoder:
			'''
			Lazily creates a transcoder if it doesn't already exist and returns it if it does.
			Also calls set on the transcoder if default is passed, before returning.
			'''
		
	@overload
	def __call__(self, cls:Type[T]) -> Union[Type[T], Type[AutoID.Interface]]:
		pass
	@overload
	def __call__(self, included_fields: Iterable[str] = [], excluded_fields: Iterable[str] = [], id_type:ID_Type=ID_Type.UUID, hashed_fields:List[str]=None) -> Callable[[Type[T]], Union[Type[T], Type[AutoID.Interface]]]:
		pass
	def __call__(self, *args, **kwargs):
		'''
		Returns a modified version of the same class,
		Union return is only here to enable suggestions in most IDEs.
		
		Note that it is expected you will latter call finalize for all
		of those changes to be applied.
		'''
		return super().__call__(*args, **kwargs)

	def decorate(self, cls: Type[T], included_fields: Iterable[str] = [], excluded_fields: Iterable[str]=[], id_type:ID_Type=ID_Type.UUID, hashed_fields:List[str]=None) -> Union[Type[T], Type[AutoID.Interface]]:
		cls = super().decorate(cls, included_fields, excluded_fields)
		cls = AutoID(id_type)(cls)
		#more cls mods in finalize!
		return cls
	
	def finalize(self):
		super().finalize()
		
		for cls in self.decorated_classes:
			classInfo = ClassInfo.get(cls)
			
			#Replace cls's getattr and setattr where each of
			#it's fields that are specified in ClassInfo.fields
			#are redirected to lazily created Transcoder instances
			
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
				if name in classInfo.fields:
					transcoder = get_transcoder(self, name, default)
					return transcoder.get()
				if default is no_default:
					return old_getattr(self, name)
				else:
					return old_getattr(self, name, default)
			def setattr(self, name:str, value):
				if name in classInfo.fields:
					transcoder = get_transcoder(self, name)
					transcoder.set(value)
				else:
					old_setattr(self, name, value)
					
			setattr(cls, "__getattr__", getattr)
			setattr(cls, "__setattr__", setattr)