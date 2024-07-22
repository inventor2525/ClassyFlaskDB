from .DirtyDecorator import DirtyDecorator
from typing import Any, Iterable
from dataclasses import MISSING
from .Args import DecodeArgs, CFInstance
from dataclasses import dataclass
from typing import Type
from .Transcoder import Transcoder

@dataclass
class ListCFInstance(CFInstance):
	list_id: str
	value_type: Type
	value_transcoder: Type[Transcoder]

@DirtyDecorator
class InstrumentedList(list):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._cf_instance:ListCFInstance = None

	def __setitem__(self, key: int, value: Any) -> None:
		if key < len(self):
			if self[key] is not value:
				self._dirty = True
		else:
			self._dirty = True
		super().__setitem__(key, value)

	def append(self, item: Any) -> None:
		self._dirty = True
		super().append(item)

	def extend(self, items: Iterable[Any]) -> None:
		self._dirty = True
		super().extend(items)

	def insert(self, index: int, item: Any) -> None:
		self._dirty = True
		super().insert(index, item)

	def pop(self, index: int = -1) -> Any:
		self._dirty = True
		return super().pop(index)

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
		value = super().__getitem__(index)
		if self._cf_instance is None:
			return value
		
		if value is MISSING:
			decode_args = self._cf_instance.decode_args.new(
				encodes=self._cf_instance.decode_args.encodes[index],
				base_name="value",
				type=self._cf_instance.value_type
			)
			value = self._cf_instance.value_transcoder.decode(decode_args)
			super().__setitem__(index, value)
		return value

	def __iter__(self):
		for i in range(len(self)):
			yield self[i]
	
	def _ensure_fully_loaded(self):
		"""Ensure all items are loaded before comparison."""
		for item in self:
			pass

	def __eq__(self, other):
		self._ensure_fully_loaded()
		if isinstance(other, InstrumentedList):
			other._ensure_fully_loaded()
		return super().__eq__(other)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		self._ensure_fully_loaded()
		return super().__hash__()