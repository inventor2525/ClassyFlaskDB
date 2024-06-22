from .DirtyDecorator import DirtyDecorator
from .Transcoder import Transcoder
from typing import Any, Mapping, Tuple

@DirtyDecorator
class InstrumentedDict(dict):
	def __init__(self, *args: Any, **kwargs: Any) -> None:
		kwargs.pop("")
		super().__init__(*args, **kwargs)
		self._dirty: bool = False
		
	def __setitem__(self, key: Any, value: Any) -> None:
		if key in self:
			if self[key] is not value:
				self._dirty = True
		else:
			self._dirty = True
		super().__setitem__(key, value)

	def update(self, other: Mapping[Any, Any]) -> None:
		self._dirty = True
		super().update(other)

	def setdefault(self, key: Any, default: Any = ...) -> Any:
		self._dirty = True
		return super().setdefault(key, default)

	def pop(self, key: Any, *args: Any) -> Any:
		self._dirty = True
		return super().pop(key, *args)

	def popitem(self) -> Tuple[Any, Any]:
		self._dirty = True
		return super().popitem()

	def clear(self) -> None:
		self._dirty = True
		super().clear()