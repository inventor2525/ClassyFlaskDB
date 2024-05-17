from abc import ABC, abstractmethod
from typing import TypeVar, Type, Any, Tuple

T = TypeVar('T')
class AnyParam(ABC):
	def __call__(self, *args, **kwargs):
		# Check if the decorator is being used with or without parenthesis
		if len(args) == 1 and callable(args[0]):
			# Without parenthesis
			return self.decorate(args[0], **kwargs)
		else:
			# With parenthesis
			return lambda obj: self.decorate(obj, *args, **kwargs)
		
	@abstractmethod
	def decorate(self, cls:Type[T], *args, **kwargs) -> Type[T]:
		pass

class SplitAnyParam(AnyParam):
	def decorate(self, cls, *args, **kwargs) -> Type[Any]:
		output_obj = self.__pre_decorate__(cls, *args, **kwargs)
		self.__post_decorate__(cls, output_obj, *args, **kwargs)
		return output_obj
	
	@abstractmethod
	def __pre_decorate__(self, origional:Type[T], *args, **kwargs) -> Type[Any]:
		'''
		Provides an opportunity to replace the original class or method with a new one.
		'''
		pass
	
	@abstractmethod
	def __post_decorate__(self, origional_obj:Type[T], output_obj:Type[Any], *args, **kwargs) -> None:
		'''
		Provides an opportunity to modify the output class or method with extra parameters latter.
		'''
		pass