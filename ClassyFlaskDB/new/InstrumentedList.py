from .DirtyDecorator import DirtyDecorator
from typing import Any, Iterable
from dataclasses import MISSING

@DirtyDecorator
class InstrumentedList(list):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._cf_instance = None

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
		if self._cf_instance is None:
			return super().__getitem__(index)
		
		if super().__getitem__(index) is MISSING:
			decode_args = DecodeArgs(
				storage_engine=self._cf_instance.storage_engine,
				parent=self._cf_instance.parent,
				field=self._cf_instance.field,
				path=self._cf_instance.path + [index]
			)
			value = self._cf_instance.value_transcoder.decode(decode_args)
			super().__setitem__(index, value)
		return super().__getitem__(index)

	def __iter__(self):
		for i in range(len(self)):
			yield self[i]