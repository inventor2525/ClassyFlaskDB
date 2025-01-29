from typing import Any, Iterable, Callable
from dataclasses import MISSING
from .Args import DecodeArgs, CFInstance
from dataclasses import dataclass, field
from typing import Type
from .Transcoder import Transcoder
from .InstrumentedValue import InstrumentedValue
from copy import deepcopy

@dataclass
class ListCFInstance(CFInstance):
	list_id: str
	value_type: Type
	value_transcoder: Type[Transcoder]

class InstrumentedList(list):
	@classmethod
	def from_cf_instance(cls, cf_instance:ListCFInstance) -> 'InstrumentedList':
		l = cls()
		l._cf_instance = cf_instance
		def load(encodes:dict):
			decode_args = cf_instance.decode_args.new(
				encodes=encodes,
				base_name="value",
				type=cf_instance.value_type
			)
			return cf_instance.value_transcoder.decode(decode_args)
		super(InstrumentedList, l).extend([
			InstrumentedValue(encodes=value_encodes, loading_func=load)
			for value_encodes in cf_instance.decode_args.encodes
		])
		return l
	
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._cf_instance:ListCFInstance = None

	def __setitem__(self, key: int, value: Any) -> None:
		self._dirty = True
		super().__setitem__(key, InstrumentedValue(value=value))

	def append(self, item: Any) -> None:
		self._dirty = True
		super().append(InstrumentedValue(value=item))

	def extend(self, items: Iterable[Any]) -> None:
		self._dirty = True
		super().extend([InstrumentedValue(value=item) for item in items])

	def insert(self, index: int, item: Any) -> None:
		self._dirty = True
		super().insert(index, InstrumentedValue(value=item))

	def pop(self, index: int = -1) -> Any:
		self._dirty = True
		item = super().pop(index)
		return item.loaded_value

	def remove(self, item: Any) -> None:
		self._dirty = True
		super().remove(item)

	def sort(self, *args, **kwargs) -> None:
		self._dirty = True
		super().sort(*args, **kwargs)

	def reverse(self) -> None:
		self._dirty = True
		super().reverse()

	def clear(self) -> None:
		self._dirty = True
		super().clear()

	def __getitem__(self, index):
		item = super().__getitem__(index)
		if isinstance(index, slice):
			return [i.loaded_value for i in item]
		return item.loaded_value
	
	def __iter__(self):
		return (item.loaded_value for item in super().__iter__())
	
	def _ensure_fully_loaded(self):
		"""Ensure all items are loaded before comparison."""
		for item in self:
			pass
	
	def __hash__(self):
		self._ensure_fully_loaded()
		return super().__hash__()

	def __deepcopy__(self, memo):
		# Check memo first
		if id(self) in memo:
			return memo[id(self)]

		# Create a new regular list using a generator
		result = list(deepcopy(item, memo) for item in self)
		
		# Store the result in memo
		memo[id(self)] = result
		
		return result
	
	def get_primary_key(self) -> str:
		return self._cf_instance.list_id
	
	def copy(self) -> list:
		return [v for v in self]