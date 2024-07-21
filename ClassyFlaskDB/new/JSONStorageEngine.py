from typing import List, Dict, Any, Type, Union, get_args, get_origin
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from .Args import MergeArgs, DecodeArgs, SetupArgs, CFInstance
from .ClassInfo import ClassInfo, ID_Type
from .DATADecorator import DATADecorator
from ClassyFlaskDB.new.StorageEngine import StorageEngine, TranscoderCollection
from ClassyFlaskDB.new.Transcoder import Transcoder, LazyLoadingTranscoder

json_transcoder_collection = TranscoderCollection()

@json_transcoder_collection.add
class JSONBasicsTranscoder(Transcoder):
    supported_types = (bool, int, float, str)

    @classmethod
    def validate(cls, type_: Type) -> bool:
        return type_ in cls.supported_types

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Any) -> None:
        merge_args.encodes[merge_args.base_name] = value

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Any:
        return decode_args.encodes[decode_args.base_name]

    @classmethod
    def hash_values(cls, value: Any, merge_args: MergeArgs, deep: bool = False) -> List[Union[str, int, float]]:
        return [value]

@json_transcoder_collection.add
class JSONDateTimeTranscoder(Transcoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return type_ == datetime

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: datetime) -> None:
        merge_args.encodes[merge_args.base_name] = value.isoformat()

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> datetime:
        return datetime.fromisoformat(decode_args.encodes[decode_args.base_name])

    @classmethod
    def hash_values(cls, value: datetime, merge_args: MergeArgs, deep: bool = False) -> List[str]:
        return [value.isoformat()]

@json_transcoder_collection.add
class JSONObjectTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return ClassInfo.has_ClassInfo(type_)

    @classmethod
    def _merge(cls, merge_args: MergeArgs, obj: Any) -> None:
        class_info = ClassInfo.get(type(obj))
        for field_name, field_info in class_info.fields.items():
            value = getattr(obj, field_name)
            transcoder = obj.__class__.__transcoders__[field_name]
            field_merge_args = merge_args.new(base_name=field_name, type=field_info.type)
            transcoder.merge(field_merge_args, value)

    @classmethod
    def _encode(cls, merge_args: MergeArgs, obj: Any) -> None:
        merge_args.encodes[f"{merge_args.base_name}_id"] = obj.get_primary_key()
        merge_args.encodes[f"{merge_args.base_name}_type"] = type(obj).__name__

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Any:
        return cls.create_lazy_instance(decode_args)

    @classmethod
    def create_lazy_instance(cls, decode_args: DecodeArgs) -> Any:
        instance = object.__new__(decode_args.type)
        setattr(instance, '_cf_instance', CFInstance(decode_args))
        
        class_info = ClassInfo.get(decode_args.type)
        for field_name in class_info.fields:
            setattr(instance, field_name, DATADecorator.not_initialized)
        
        if hasattr(instance, '__post_init__'):
            instance.__post_init__()
        
        return instance

    @classmethod
    def hash_values(cls, value: Any, merge_args: MergeArgs, deep: bool = False) -> List[str]:
        class_info = ClassInfo.get(type(value))
        if deep and class_info.id_type == ID_Type.HASHID:
            value.new_id(deep=True)
        return [value.get_primary_key()]

@json_transcoder_collection.add
class JSONEnumTranscoder(Transcoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return issubclass(type_, Enum)

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Enum) -> None:
        merge_args.encodes[merge_args.base_name] = value.name

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Enum:
        return decode_args.type[decode_args.encodes[decode_args.base_name]]

    @classmethod
    def hash_values(cls, value: Enum, merge_args: MergeArgs, deep: bool = False) -> List[str]:
        return [value.name]

@json_transcoder_collection.add
class JSONListTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return getattr(type_, "__origin__", None) is list

    @classmethod
    def _merge(cls, merge_args: MergeArgs, value: List[Any]) -> None:
        value_type = get_args(merge_args.type)[0]
        value_transcoder = merge_args.storage_engine.get_transcoder_type(value_type)
        
        encoded_list = []
        for index, item in enumerate(value):
            item_merge_args = merge_args.new(
                base_name=f"{merge_args.base_name}_{index}",
                type=value_type
            )
            value_transcoder.merge(item_merge_args, item)
            encoded_list.append(item_merge_args.encodes)
        
        merge_args.encodes[merge_args.base_name] = encoded_list

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> List[Any]:
        return cls.create_lazy_instance(decode_args)

    @classmethod
    def create_lazy_instance(cls, decode_args: DecodeArgs) -> List[Any]:
        lazy_list = []
        value_type = get_args(decode_args.type)[0]
        value_transcoder = decode_args.storage_engine.get_transcoder_type(value_type)
        
        for index, item_encodes in enumerate(decode_args.encodes[decode_args.base_name]):
            item_decode_args = decode_args.new(
                encodes=item_encodes,
                base_name=f"{decode_args.base_name}_{index}",
                type=value_type
            )
            lazy_list.append(value_transcoder.create_lazy_instance(item_decode_args))
        
        return lazy_list

    @classmethod
    def hash_values(cls, value: List[Any], merge_args: MergeArgs, deep: bool = False) -> List[Any]:
        h = []
        value_type = get_args(merge_args.type)[0]
        value_transcoder = merge_args.storage_engine.get_transcoder_type(value_type)
        for index, item in enumerate(value):
            item_merge_args = merge_args.new(
                base_name=f"{merge_args.base_name}_{index}",
                type=value_type
            )
            h.extend(value_transcoder.hash_values(item, item_merge_args, deep))
        return h

@json_transcoder_collection.add
class JSONDictionaryTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return getattr(type_, "__origin__", None) is dict

    @classmethod
    def _merge(cls, merge_args: MergeArgs, value: Dict[Any, Any]) -> None:
        key_type, value_type = get_args(merge_args.type)
        key_transcoder = merge_args.storage_engine.get_transcoder_type(key_type)
        value_transcoder = merge_args.storage_engine.get_transcoder_type(value_type)
        
        encoded_dict = {}
        for k, v in value.items():
            key_merge_args = merge_args.new(base_name=f"{merge_args.base_name}_key", type=key_type)
            value_merge_args = merge_args.new(base_name=f"{merge_args.base_name}_value", type=value_type)
            
            key_transcoder.merge(key_merge_args, k)
            value_transcoder.merge(value_merge_args, v)
            
            encoded_dict[key_merge_args.encodes[f"{merge_args.base_name}_key"]] = value_merge_args.encodes
        
        merge_args.encodes[merge_args.base_name] = encoded_dict

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Dict[Any, Any]:
        return cls.create_lazy_instance(decode_args)

    @classmethod
    def create_lazy_instance(cls, decode_args: DecodeArgs) -> Dict[Any, Any]:
        lazy_dict = {}
        key_type, value_type = get_args(decode_args.type)
        key_transcoder = decode_args.storage_engine.get_transcoder_type(key_type)
        value_transcoder = decode_args.storage_engine.get_transcoder_type(value_type)
        
        for encoded_key, encoded_value in decode_args.encodes[decode_args.base_name].items():
            key_decode_args = decode_args.new(
                encodes={f"{decode_args.base_name}_key": encoded_key},
                base_name=f"{decode_args.base_name}_key",
                type=key_type
            )
            value_decode_args = decode_args.new(
                encodes=encoded_value,
                base_name=f"{decode_args.base_name}_value",
                type=value_type
            )
            
            lazy_key = key_transcoder.decode(key_decode_args)
            lazy_value = value_transcoder.create_lazy_instance(value_decode_args)
            
            lazy_dict[lazy_key] = lazy_value
        
        return lazy_dict

    @classmethod
    def hash_values(cls, value: Dict[Any, Any], merge_args: MergeArgs, deep: bool = False) -> List[Any]:
        h = []
        key_type, value_type = get_args(merge_args.type)
        key_transcoder = merge_args.storage_engine.get_transcoder_type(key_type)
        value_transcoder = merge_args.storage_engine.get_transcoder_type(value_type)
        for k, v in value.items():
            key_merge_args = merge_args.new(base_name=f"{merge_args.base_name}_key", type=key_type)
            value_merge_args = merge_args.new(base_name=f"{merge_args.base_name}_value", type=value_type)
            h.extend(key_transcoder.hash_values(k, key_merge_args, deep))
            h.extend(value_transcoder.hash_values(v, value_merge_args, deep))
        return h