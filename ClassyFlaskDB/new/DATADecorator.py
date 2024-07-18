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
		__transcoders__:Dict[str, Transcoder]
		_cf_instance: Optional['CFInstance'] = None
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
		self.storage_engine = storage_engine
		
		for cls in self.registry.values():
			classInfo = ClassInfo.get(cls)
			
			cls.__transcoders__ = {}
			for field_name, field_info in classInfo.fields.items():
				transcoder_type = self.storage_engine.get_transcoder_type(field_info.type)
				cls.__transcoders__[field_name] = transcoder_type()	
				
			old_getattr = cls.__getattribute__
			
			def __getattribute__(self:'DATADecorator.Interface', name:str):
				cf_instance = CFInstance.get(self)
				if cf_instance is not MISSING and cf_instance is not None:
					self_type = type(self)
					class_info = ClassInfo.get(self_type)
					
					if name in class_info.fields and name not in cf_instance.loaded_fields:
						field = class_info.fields[name]
						transcoder = self_type.__transcoders__[name]
						decode_args = cf_instance.decode_args.new(
							base_name = field.name,
							type = field.type
						)
						value = transcoder.decode(decode_args)
						object.__setattr__(self, name, value)
						cf_instance.loaded_fields.add(name)
						return value
					
				return old_getattr(self, name)

			cls.__getattribute__ = __getattribute__