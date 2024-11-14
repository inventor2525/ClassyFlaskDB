from dataclasses import dataclass
from typing import Any, Callable

MISSING = object()
@dataclass
class InstrumentedValue:
	encodes:dict = MISSING
	value:Any = MISSING
	loading_func:Callable[[dict],Any] = None
	
	@property
	def loaded_value(self):
		self.ensure_loaded()
		return self.value
	@loaded_value.setter
	def loaded_value(self, new):
		self.encodes = MISSING
		self.value = new
		
	def ensure_loaded(self) -> bool:
		if self.value is MISSING:
			if self.loading_func and self.encodes is not MISSING:
				self.value = self.loading_func(self.encodes)
				return True
			return False
		return True
		
	def __eq__(self, value: object) -> bool:
		if isinstance(value, InstrumentedValue):
			if self.value is MISSING or value.value is MISSING:
				if self.encodes is not MISSING and value.encodes is not MISSING:
					return self.encodes == value.encodes
				if not (self.ensure_loaded() and value.ensure_loaded()):
					return False
			return self.value == value.value
		else:
			if self.ensure_loaded():
				return self.value == value
			return False
	
	def __ne__(self, value: object) -> bool:
		return not self.__eq__(value)
	
	def __hash__(self) -> int:
		return hash(self.loaded_value)