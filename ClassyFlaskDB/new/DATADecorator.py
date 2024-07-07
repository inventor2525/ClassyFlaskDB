from ClassyFlaskDB.DATA.ID_Type import ID_Type
from .InfoDecorator import *
from .Transcoder import *
from .StorageEngine import *
from .AutoID import *
from .DirtyDecorator import *

@dataclass
class DATADecorator(InfoDecorator):
	not_initialized = object()
	'''
	A class decorator that replaces all specified fields with 'Transcoder'
	instances that facilitate (optionally lazy) loading of objects from
	the passed generic storage engine.
	
	This also applies, to each decorated class, a ClassInfo and auto ID.
	
	Note: Remember to call finalize after every decorated class is imported!
	'''
	
	class Interface(AutoID.Interface, DirtyDecorator.Interface):
		__transcoders__:List[Transcoder]
		'''These are only those that have had their fields 'poked' so far. Use __get_transcoder__ if you want to do some digging.'''
		def __get_transcoder__(self, name:str, default=object()) -> Transcoder:
			'''
			Lazily creates a transcoder if it doesn't already exist and returns it if it does.
			Also calls set on the transcoder if default is passed, before returning.
			'''
			pass
		
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
	
	def finalize(self, storage_engine: StorageEngine):
		super().finalize()
		
		for cls in self.registry.values():
			classInfo = ClassInfo.get(cls)
			
			old_getattr = cls.__getattribute__
			
			def safe_hasattr(obj, name):
				try:
					object.__getattribute__(obj, name)
					return True
				except AttributeError:
					return False
			
			def __getattribute__(self, name):
				if safe_hasattr(self, '_cf_instance'):
					cf_instance = object.__getattribute__(self, '_cf_instance')
					class_info = ClassInfo.get(type(self))
					
					if name in class_info.fields and name not in cf_instance.loaded_fields:
						field = class_info.fields[name]
						transcoder = self.__class__.__transcoders__[name]
						value = transcoder.decode(cf_instance, field)
						object.__setattr__(self, name, value)
						cf_instance.loaded_fields.add(name)
						return value
					
				return old_getattr(self, name)

			cls.__getattribute__ = __getattribute__