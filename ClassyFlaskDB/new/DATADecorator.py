from ClassyFlaskDB.DATA.ID_Type import ID_Type
from .InfoDecorator import *
from .Transcoder import *
from .StorageEngine import *
from .AutoID import *
from .DirtyDecorator import *
from copy import deepcopy

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
	def __call__(self, cls:Type[T]) -> Union[Type[T], Type['DATADecorator.Interface']]:
		pass
	@overload
	def __call__(self, included_fields: Iterable[str] = [], excluded_fields: Iterable[str] = [], id_type:ID_Type=ID_Type.UUID, hashed_fields:List[str]=None) -> Callable[[Type[T]], Union[Type[T], Type['DATADecorator.Interface']]]:
		pass
	def __call__(self, *args, **kwargs):
		'''
		Returns a modified version of the same class,
		Union return is only here to enable suggestions in most IDEs.
		
		Note that it is expected you will latter call finalize for all
		of those changes to be applied.
		'''
		return super().__call__(*args, **kwargs)

	def decorate(self, cls: Type[T], included_fields: Iterable[str] = [], excluded_fields: Iterable[str]=[], id_type:ID_Type=ID_Type.UUID, hashed_fields:List[str]=None) -> Union[Type[T], Type['DATADecorator.Interface']]:
		cls = super().decorate(cls, included_fields, excluded_fields)
		cls = AutoID(id_type, None if hashed_fields is None else set(hashed_fields))(cls)
		#more cls mods in finalize!
		return cls
	
	def _finalize(self):
		super()._finalize()
		
		from .InstrumentedList import InstrumentedList
		from .InstrumentedDict import InstrumentedDict

		data_decorator_applied = object()
		for cls in self.registry.values():
			#Apply a new get attribute to cls:
			old_getattr = cls.__getattribute__
			if not hasattr(old_getattr, "data_decorator_applied"):
				def __getattribute__(self:'DATADecorator.Interface', field_name:str):
					print(f"Getting {field_name}")
					cf_instance = CFInstance.get(self)
					if cf_instance is not MISSING and cf_instance is not None:
						class_info = ClassInfo.get(type(self))
						print(f"   has cf instance")
						
						if field_name in cf_instance.unloaded_fields:
							field = class_info.fields[field_name]
							transcoder = cf_instance.decode_args.storage_engine.get_transcoder_type(field.type)
							decode_args = cf_instance.decode_args.new(
								base_name = field_name,
								type = field.type
							)
							print(f"       is in un-loaded fields")
							try:
								value = transcoder.decode(decode_args)
								print(f"           decoded!")
							except Exception as e:
								if field.default is not MISSING:
									value = field.default
								elif field.default_factory is not MISSING:
									value = field.default_factory()
								else:
									raise ValueError(f"We attempted to deserialize a value for {class_info.semi_qualname}.{field_name} but could not because of {e}, and {field_name} does not provide for a default or default_factory.")
							print("   setting...")
							object.__setattr__(self, field_name, value)
							print("   getter set value!")
							cf_instance.unloaded_fields.remove(field_name)
							print(" removed from unloaded_fields!")
							return value
					print(" defaulting to old getter...")
					return object.__getattribute__(self, field_name)

				cls.__getattribute__ = __getattribute__
				cls.__getattribute__.data_decorator_applied = data_decorator_applied
			
			# Apply a new __setattr__ to cls:
			old_setattr = cls.__setattr__
			if not hasattr(old_setattr, "data_decorator_applied"):
				def __setattr__(self, name, value):
					if getattr(self, '__custom_setter_enabled__', False):
						print(f"Setting {name} to {value}")
						cf_instance = CFInstance.get(self)
						if cf_instance is not MISSING and cf_instance is not None:
							if name in cf_instance.unloaded_fields:
								cf_instance.unloaded_fields.remove(name)
								print("    removed from unloaded_fields")
					old_setattr(self, name, value)
					if getattr(self, '__custom_setter_enabled__', False):
						print(" set!")

				cls.__setattr__ = __setattr__
				cls.__setattr__.data_decorator_applied = data_decorator_applied
			#Add a deepcopy method to cls:
			def __deepcopy__(self, memo):
				if id(self) in memo:
					return memo[id(self)]

				class_info = ClassInfo.get(self.__class__)
				
				# Create a new instance directly
				cls_copy = object.__new__(self.__class__)
				memo[id(self)] = cls_copy

				for field_name, field_info in class_info.fields.items():
					value = getattr(self, field_name, None)
					if value is not None:
						if isinstance(value, InstrumentedList):
							setattr(cls_copy, field_name, deepcopy(list(value), memo))
						elif isinstance(value, InstrumentedDict):
							setattr(cls_copy, field_name, deepcopy(dict(value), memo))
						else:
							try:
								setattr(cls_copy, field_name, deepcopy(value, memo))
							except:
								try:
									setattr(cls_copy, field_name, None)
								except:
									pass
					elif field_info.default is not MISSING:
						setattr(cls_copy, field_name, field_info.default)
					elif field_info.default_factory is not MISSING:
						setattr(cls_copy, field_name, field_info.default_factory())

				if hasattr(cls_copy, '__post_init__'):
					cls_copy.__post_init__()

				return cls_copy

			setattr(cls, '__deepcopy__', __deepcopy__)
		print("done")