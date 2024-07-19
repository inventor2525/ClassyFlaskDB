from .DirtyDecorator import DirtyDecorator
from .Transcoder import Transcoder
from typing import Any, Mapping, Tuple, Dict, Type, TypeVar
from dataclasses import dataclass, MISSING
from .Args import CFInstance

K = TypeVar('K')
V = TypeVar('V')

@dataclass
class DictCFInstance(CFInstance):
    dict_id: str
    key_type: Type
    value_type: Type
    key_transcoder: Type[Transcoder]
    value_transcoder: Type[Transcoder]
	
@DirtyDecorator
class InstrumentedDict(dict):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._cf_instance: DictCFInstance = None

	def __setitem__(self, key: K, value: V) -> None:
		if key in self:
			if self[key] is not value:
				self._dirty = True
		else:
			self._dirty = True
		super().__setitem__(key, value)

	def __getitem__(self, key: K) -> V:
		value = super().get(key, MISSING)
		if self._cf_instance is None or value is not MISSING:
			return value

		decode_args = self._cf_instance.decode_args.new(
			encodes=self._cf_instance.decode_args.encodes[key],
			base_name="value",
			type=self._cf_instance.value_type
		)
		value = self._cf_instance.value_transcoder.decode(decode_args)
		super().__setitem__(key, value)
		return value
	
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