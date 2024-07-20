from .ClassInfo import *
from dataclasses import dataclass, Field
from abc import ABC, abstractmethod, abstractclassmethod
from .Args import *
	
class Transcoder:
    @classmethod
    def check_overridden(cls, func):
        func_name = func.__name__
        if hasattr(cls, func_name):
            cls_func = getattr(cls, func_name)
            if cls_func != func:
                return True
        return False
    
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
    def _encode(cls, merge_args: MergeArgs, value: Any) -> None:
        pass

    @classmethod
    def merge(cls, merge_args: MergeArgs, value: Any) -> None:
        if cls.check_overridden(Transcoder._merge):
            different_storage_engine = False
            cf_instance = CFInstance.get(value)
            if cf_instance is not MISSING:
                if cf_instance.decode_args.storage_engine != merge_args.storage_engine:
                    different_storage_engine = True
            
            # Always merge if a different storage engine,
            # was used for query of something we are now merging,
            # otherwise do so if this object is dirty:
            if different_storage_engine or merge_args.is_dirty.get(id(value), True):
                merge_args.is_dirty[id(value)] = False
                cls._merge(merge_args, value)
        cls._encode(merge_args, value)

    @classmethod
    def decode(cls, storage_engine: Any, obj: Any, field_name: str, encoded_values: Dict[str, Any]) -> Any:
        return None

class LazyLoadingTranscoder(Transcoder):
    @classmethod
    def create_lazy_instance(self, cf_instance: CFInstance) -> Any:
        pass