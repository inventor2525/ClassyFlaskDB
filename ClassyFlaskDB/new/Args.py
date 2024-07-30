from dataclasses import dataclass, Field, field, fields, MISSING
from typing import Any, Dict, Optional, List, Union, TypeVar, Type, Set, Literal
from .StorageEngine import StorageEngine
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
	storage_engine: StorageEngine = field(kw_only=True)
	context: Dict[str, Any] = field(kw_only=True)
	is_dirty: Dict[int, bool] = field(kw_only=True)
	encodes: Dict[str, Any] = field(kw_only=True)
	base_name: str = field(kw_only=True)
	type: Type = field(kw_only=True)
	merge_depth_limit:int = field(default=-1, kw_only=True)
	depth:int = field(default=0, kw_only=True)
	
	def new(self: T, *, same_depth: bool = False, **kwargs) -> T:
		if same_depth:
			if self.merge_depth_limit > -1:
				# we need to re-consider depth limits here so we don't end up deleting the list and then get limited out of merging it
				kwargs['depth'] = kwargs.get("depth", self.depth - 1)
		
		args_ = super().new(**kwargs)
		args_.depth += 1
		return args_

@dataclass
class SetupArgs(Args):
	storage_engine: StorageEngine = field(kw_only=True)
	class_info: ClassInfo = field(kw_only=True)

@dataclass
class DecodeArgs(Args):
	storage_engine: StorageEngine = field(kw_only=True)
	encodes: Dict[str, Any] = field(kw_only=True)
	base_name: str = field(kw_only=True)
	type: Type = field(kw_only=True)
	
@dataclass
class CFInstance(Args):
	decode_args: DecodeArgs = field(kw_only=True)
	unloaded_fields: Set[str] = field(default_factory=set, kw_only=True)
	
	@staticmethod
	def get(self) -> Union['CFInstance',Literal[MISSING]]:
		try:
			val = object.__getattribute__(self, '_cf_instance')
			return val
		except AttributeError:
			return MISSING