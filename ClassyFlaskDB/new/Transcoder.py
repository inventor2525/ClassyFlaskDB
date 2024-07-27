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
    
    @abstractclassmethod
    def validate(cls, type_: Type) -> bool:
        return False

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool):
        pass

    @classmethod
    def _merge(cls, merge_args: MergeArgs, value: Any) -> None:
        pass
    
    @abstractclassmethod
    def _encode(cls, merge_args: MergeArgs, value: Any) -> None:
        pass

    @classmethod
    def merge(cls, merge_args: MergeArgs, value: Any) -> None:
        if value is None:
            return
        
        if merge_args.merge_depth_limit > -1:
            if merge_args.depth > merge_args.merge_depth_limit:
                return
        
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

    @abstractclassmethod
    def decode(cls, decode_args: DecodeArgs) -> Any:
        return None

class LazyLoadingTranscoder(Transcoder):
    @abstractclassmethod
    def create_lazy_instance(self, cf_instance: CFInstance) -> Any:
        '''
        Creates an instance of a queried object, having in it's
        _cf_instance all it needs to decode it's fields lazily
        as they are first accessed.
        '''
        ...