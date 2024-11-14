from dataclasses import dataclass, field, MISSING
from typing import Any, Dict, List, Type, Iterator
from .InstrumentedValue import InstrumentedValue
from .Args import DecodeArgs, CFInstance
from .Transcoder import Transcoder
from typing import get_args
from copy import deepcopy

@dataclass
class DictCFInstance(CFInstance):
	dict_id: str
	key_transcoder: Type[Transcoder]
	value_transcoder: Type[Transcoder]

class InstrumentedDict(dict):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._cf_instance: DictCFInstance = None

	@classmethod
	def from_cf_instance(cls, cf_instance: DictCFInstance) -> 'InstrumentedDict':
		instance = cls()
		instance._cf_instance = cf_instance
		
		def key_load(encodes:dict):
			key_decode_args = cf_instance.decode_args.new(
				encodes=encodes,
				base_name="key",
				type=get_args(cf_instance.decode_args.type)[0]
			)
			return cf_instance.key_transcoder.decode(key_decode_args)
		
		def value_load(encodes:dict):
			value_decode_args = cf_instance.decode_args.new(
				encodes=encodes,
				base_name="value",
				type=get_args(cf_instance.decode_args.type)[1]
			)
			return cf_instance.value_transcoder.decode(value_decode_args)
		
		for encoded_item in cf_instance.decode_args.encodes:
			key = InstrumentedValue(encodes=encoded_item, loading_func=key_load)
			value = InstrumentedValue(encodes=encoded_item, loading_func=value_load)
			super(InstrumentedDict, instance).__setitem__(key, value)
		return instance
	
	def __setitem__(self, key, value) -> None:
		self._dirty = True
		k = InstrumentedValue(value=key)
		v = InstrumentedValue(value=value)
		super().__setitem__(k, v)

	def __getitem__(self, key):
		item = super().__getitem__(key)
		return item.loaded_value

	def keys(self) -> Iterator[Any]:
		return (key.loaded_value for key in super().keys())

	def values(self) -> Iterator[Any]:
		return (value.loaded_value for value in super().values())

	def items(self) -> Iterator[tuple[Any, Any]]:
		return ((key.loaded_value, value.loaded_value) for key,value in super().items())

	def pop(self, key, default=MISSING):
		if default is not MISSING:
			value = super().pop(key, default)
		else:
			value = super().pop(key)
		return value.loaded_value

	def popitem(self):
		key,value = super().popitem()
		return key.loaded_value, value.loaded_value

	def update(self, *args, **kwargs):
		if args:
			other = args[0]
			if isinstance(other, dict):
				for key in other:
					self[key] = other[key]
			elif hasattr(other, "keys"):
				for key in other.keys():
					self[key] = other[key]
			else:
				for key, value in other:
					self[key] = value
		for key, value in kwargs.items():
			self[key] = value
	
	def _ensure_fully_loaded(self):
		"""Ensure all items are loaded before comparison."""
		for k,v in self.items():
			pass

	def __hash__(self):
		self._ensure_fully_loaded()
		return super().__hash__()
	
	def __deepcopy__(self, memo):
		# Check memo first
		if id(self) in memo:
			return memo[id(self)]

		# Create a new regular dict using a generator
		result = dict((deepcopy(key, memo), deepcopy(value, memo))
					for key, value in self.items())
		
		# Store the result in memo
		memo[id(self)] = result
		
		return result
	
	def get_primary_key(self) -> str:
		return self._cf_instance.dict_id
	
	def __iter__(self):
		return (item.loaded_value for item in super().__iter__())