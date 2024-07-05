from .ClassInfo import *
from dataclasses import dataclass, Field
from abc import ABC, abstractmethod, abstractclassmethod
from .Args import *
	
class Transcoder:
    @classmethod
    def validate(cls, class_info: ClassInfo, field: Field) -> bool:
        return False

    @classmethod
    def setup(cls, class_info: ClassInfo, field: Field, is_primary_key: bool) -> List[Any]:
        return []

    @classmethod
    def _merge(cls, merge_args: MergeArgs, value: Any) -> None:
        pass

    @classmethod
    def merge(cls, merge_args: MergeArgs, value: Any) -> None:
        return cls._merge(merge_args, value)
        if merge_args.is_dirty.get(id(value), True):
            cls._merge(merge_args, value)
            merge_args.is_dirty[id(value)] = False

    @classmethod
    def get_columns(cls, class_info: ClassInfo, field: Field) -> List[str]:
        return []

    @classmethod
    def decode(cls, storage_engine: Any, obj: Any, field_name: str, encoded_values: Dict[str, Any]) -> Any:
        return None