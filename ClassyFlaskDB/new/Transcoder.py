from .ClassInfo import *
from dataclasses import dataclass, Field
from abc import ABC, abstractmethod, abstractclassmethod
from .Args import *
	
class Transcoder:
    @classmethod
    def validate(cls, class_info: ClassInfo, field: Field) -> bool:
        return False

    @classmethod
    def setup(cls, setup_args: SetupArgs, field: Field):
        pass

    @classmethod
    def _merge(cls, merge_args: MergeArgs, value: Any) -> None:
        pass

    @classmethod
    def merge(cls, merge_args: MergeArgs, value: Any) -> None:
        try:
            cf_instance = object.__getattribute__(value, '_cf_instance')
            if cf_instance.storage_engine != merge_args.storage_engine or merge_args.is_dirty.get(id(value), True):
                cls._merge(merge_args, value)
                merge_args.is_dirty[id(value)] = False
        except AttributeError:
            cls._merge(merge_args, value)

    @classmethod
    def get_columns(cls, class_info: ClassInfo, field: Field) -> List[str]:
        return []

    @classmethod
    def decode(cls, storage_engine: Any, obj: Any, field_name: str, encoded_values: Dict[str, Any]) -> Any:
        return None

class LazyLoadingTranscoder(Transcoder):
    @classmethod
    def create_lazy_instance(self, storage_engine: 'StorageEngine', cls: Type, encoded_values: Dict[str, Any]) -> Any:
        pass