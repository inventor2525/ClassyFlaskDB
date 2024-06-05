from abc import ABC, abstractmethod
from typing import Dict, Any, Type, TypeVar, Iterator, Generic, List, overload
from dataclasses import dataclass, field

T = TypeVar('T')
class StorageEngineContext(ABC, Generic[T]):
	pass