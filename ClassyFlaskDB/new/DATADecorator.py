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
		_cf_instance: Optional['CFInstance'] = None
		
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
			old_getattr = cls.__getattribute__
			
			def __getattribute__(self:'DATADecorator.Interface', field_name:str):
				cf_instance = CFInstance.get(self)
				if cf_instance is not MISSING and cf_instance is not None:
					class_info = ClassInfo.get(type(self))
					
					if field_name in class_info.fields and field_name not in cf_instance.loaded_fields:
						field = class_info.fields[field_name]
						transcoder = cf_instance.decode_args.storage_engine.get_transcoder_type(field.type)
						decode_args = cf_instance.decode_args.new(
							base_name = field_name,
							type = field.type
						)
						value = transcoder.decode(decode_args)
						object.__setattr__(self, field_name, value)
						cf_instance.loaded_fields.add(field_name)
						return value
					
				return old_getattr(self, field_name)

			cls.__getattribute__ = __getattribute__