from dataclasses import dataclass, Field, field, fields, MISSING
from typing import Any, Dict, Optional, List, Union, TypeVar, Type, Set, Literal
from .ClassInfo import ClassInfo

T = TypeVar('T', bound='Args')

@dataclass
class Args:
	def new(self: T, **kwargs) -> T:
		"""
		Create a new instance of the current Args class with selective updates.

		This method creates a shallow copy of the current instance and updates it
		with the provided keyword arguments. It allows for easy creation of new
		Args instances with specific changes while maintaining the values of
		unspecified fields.

		Args:
			**kwargs: Keyword arguments representing the fields to be updated
					in the new instance.

		Returns:
			A new instance of the same Args subclass with the specified updates.

		Example:
			original_args = SomeArgsSubclass(field1=1, field2="a", field3=[1, 2, 3])
			new_args = original_args.new(field2="b", field3=[4, 5, 6])
			# new_args will have field1=1, field2="b", field3=[4, 5, 6]
		"""
		new_data = {}
		for f in fields(self):
			if f.name in kwargs:
				new_data[f.name] = kwargs[f.name]
			elif isinstance(f.type, type) and issubclass(f.type, Args):
				new_data[f.name] = getattr(self, f.name).new()
			else:
				new_data[f.name] = getattr(self, f.name)
		return type(self)(**new_data)

@dataclass
class MergeArgs(Args):
	storage_engine: 'StorageEngine' = field(kw_only=True)
	context: Dict[str, Any] = field(kw_only=True)
	is_dirty: Dict[int, bool] = field(kw_only=True)
	encodes: Dict[str, Any] = field(kw_only=True)
	base_name: str = field(kw_only=True)
	type: Type = field(kw_only=True)


@dataclass
class SetupArgs(Args):
	storage_engine: 'StorageEngine' = field(kw_only=True)
	class_info: ClassInfo = field(kw_only=True)

@dataclass
class DecodeArgs(Args):
	storage_engine: 'StorageEngine' = field(kw_only=True)
	encodes: Dict[str, Any] = field(kw_only=True)
	base_name: str = field(kw_only=True)
	type: Type = field(kw_only=True)
	#TODO: depth:int (one of the things that makes these args classes great is now in new we can incorporate a auto incremented number for 'depth' and only merge up to a depth limit)
	
@dataclass
class CFInstance(Args):
	decode_args: DecodeArgs = field(kw_only=True)
	loaded_fields: Set[str] = field(default_factory=set, kw_only=True)
	
	@staticmethod
	def get(self) -> Union['CFInstance',Literal[MISSING]]:
		try:
			val = object.__getattribute__(self, '_cf_instance')
			return val
		except AttributeError:
			return MISSING