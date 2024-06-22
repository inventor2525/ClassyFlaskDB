from .DirtyDecorator import DirtyDecorator
from typing import Any, Iterable

@DirtyDecorator
class InstrumentedList(list):
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