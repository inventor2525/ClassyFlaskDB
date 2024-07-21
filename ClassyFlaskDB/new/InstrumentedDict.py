from dataclasses import dataclass, field
from typing import Any, Dict, List, Type, Iterator
from .Args import DecodeArgs, CFInstance
from .DirtyDecorator import DirtyDecorator
from .Transcoder import Transcoder
from typing import get_args

MISSING = object()

@dataclass
class InstrumentedItem:
	encodes_row: Dict[str, Any]
	key: Any = field(default=MISSING)
	value: Any = field(default=MISSING)

@dataclass
class DictCFInstance(CFInstance):
	dict_id: str
	key_transcoder: Type[Transcoder]
	value_transcoder: Type[Transcoder]

@DirtyDecorator
class InstrumentedDict(dict):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._cf_instance: DictCFInstance = None
		self.__items__: List[InstrumentedItem] = []

	@classmethod
	def from_cf_instance(cls, cf_instance: DictCFInstance) -> 'InstrumentedDict':
		instance = cls()
		instance._cf_instance = cf_instance
		instance.__items__ = [
			InstrumentedItem(encodes_row=row)
			for row in cf_instance.decode_args.encodes
		]
		return instance
	
	def __setitem__(self, key, value) -> None:
		if key in self:
			if self[key] is not value:
				self._dirty = True
				# Update the existing item
				for item in self.__items__:
					if item.key == key:
						item.value = value
						break
		else:
			self._dirty = True
			# Add a new item
			self.__items__.append(InstrumentedItem({}, key, value))
		super().__setitem__(key, value)

	def __getitem__(self, key):
		try:
			value = super().__getitem__(key)
			if isinstance(value, InstrumentedItem):
				decoded_value = self._decode_value(value)
				super().__setitem__(key, decoded_value)
				return decoded_value
			return value
		except KeyError:
			if self._cf_instance is None:
				raise

			for k, item in zip(self.keys(), self.__items__):
				if k == key:
					value = item.value
					if value is MISSING:
						value = self._decode_value(item)
						super().__setitem__(k, value)
					return value
			raise KeyError(key)

	def _decode_key(self, item: InstrumentedItem) -> Any:
		if item.key is MISSING:
			key_decode_args = self._cf_instance.decode_args.new(
				encodes=item.encodes_row,
				base_name="key",
				type=get_args(self._cf_instance.decode_args.type)[0]
			)
			item.key = self._cf_instance.key_transcoder.decode(key_decode_args)
		return item.key

	def _decode_value(self, item: InstrumentedItem) -> Any:
		if item.value is MISSING:
			value_decode_args = self._cf_instance.decode_args.new(
				encodes=item.encodes_row,
				base_name="value",
				type=get_args(self._cf_instance.decode_args.type)[1]
			)
			item.value = self._cf_instance.value_transcoder.decode(value_decode_args)
		return item.value

	def keys(self) -> Iterator[Any]:
		for item in self.__items__:
			key = self._decode_key(item)
			if key not in self:
				super().__setitem__(key, item)
			yield key

	def values(self) -> Iterator[Any]:
		for item in self.__items__:
			yield self._decode_value(item)

	def items(self) -> Iterator[tuple[Any, Any]]:
		for item in self.__items__:
			key = self._decode_key(item)
			value = self._decode_value(item)
			if key not in self:
				super().__setitem__(key, value)
			yield key, value

	def pop(self, key, default=MISSING):
		for i, item in enumerate(self.__items__):
			if self._decode_key(item) == key:
				del self.__items__[i]
				return super().pop(key, default)
		if default is MISSING:
			raise KeyError(key)
		return default

	def popitem(self):
		if not self.__items__:
			raise KeyError('dictionary is empty')
		item = self.__items__.pop()
		key = self._decode_key(item)
		value = self._decode_value(item)
		super().__delitem__(key)
		return key, value

	def clear(self):
		self.__items__.clear()
		super().clear()

	def update(self, *args, **kwargs):
		if len(args) > 1:
			raise TypeError('update expected at most 1 argument, got %d' % len(args))
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

	def setdefault(self, key, default=None):
		if key in self:
			return self[key]
		self[key] = default
		return default
	
	def _ensure_fully_loaded(self):
		"""Ensure all items are loaded before comparison."""
		for k,v in self.items():
			pass

	def __eq__(self, other):
		if isinstance(other, InstrumentedDict):
			self._ensure_fully_loaded()
			other._ensure_fully_loaded()
		elif isinstance(other, dict):
			self._ensure_fully_loaded()
		return super().__eq__(other)

	def __ne__(self, other):
		return not self.__eq__(other)

	def __hash__(self):
		self._ensure_fully_loaded()
		return super().__hash__()