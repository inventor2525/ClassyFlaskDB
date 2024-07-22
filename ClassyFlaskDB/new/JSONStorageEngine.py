from typing import List, Dict, Any, Type, Union, get_args, get_origin
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, MISSING
from .Args import MergeArgs, DecodeArgs, SetupArgs, CFInstance
from .ClassInfo import ClassInfo, ID_Type
from .DATADecorator import DATADecorator
from ClassyFlaskDB.new.StorageEngine import StorageEngine, TranscoderCollection
from ClassyFlaskDB.new.Transcoder import Transcoder, LazyLoadingTranscoder
from .InstrumentedList import InstrumentedList
import uuid

json_transcoder_collection = TranscoderCollection()

@dataclass
class JSONMergeArgs(MergeArgs):
    root_dict: Dict[str, Dict[str, Dict[str, Any]]]

@dataclass
class JSONDecodeArgs(DecodeArgs):
    root_dict: Dict[str, Dict[str, Dict[str, Any]]]

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
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> None:
        table_name = f"obj_{ClassInfo.get_semi_qual_name(type_)}"
        if table_name not in setup_args.storage_engine.root_dict:
            setup_args.storage_engine.root_dict[table_name] = {}

    @classmethod
    def _merge(cls, merge_args: JSONMergeArgs, obj: Any) -> None:
        class_info = ClassInfo.get(type(obj))
        table_name = f"obj_{ClassInfo.get_semi_qual_name(type(obj))}"
        row = {}
        
        for field_name, field_info in class_info.fields.items():
            value = getattr(obj, field_name)
            transcoder = merge_args.storage_engine.get_transcoder_type(field_info.type)
            field_merge_args = merge_args.new(base_name=field_name, type=field_info.type)
            transcoder.merge(field_merge_args, value)
            row.update(field_merge_args.encodes)
        
        merge_args.root_dict[table_name][obj.get_primary_key()] = row

    @classmethod
    def _encode(cls, merge_args: JSONMergeArgs, obj: Any) -> None:
        merge_args.encodes[f"{merge_args.base_name}_id"] = obj.get_primary_key()
        merge_args.encodes[f"{merge_args.base_name}_type"] = ClassInfo.get_semi_qual_name(type(obj))

    @classmethod
    def decode(cls, decode_args: JSONDecodeArgs) -> Any:
        return cls.create_lazy_instance(CFInstance(decode_args))

    @classmethod
    def create_lazy_instance(cls, cf_instance: CFInstance) -> Any:
        instance = object.__new__(cf_instance.decode_args.type)
        setattr(instance, '_cf_instance', cf_instance)
        
        class_info = ClassInfo.get(cf_instance.decode_args.type)
        for field_name in class_info.fields:
            setattr(instance, field_name, DATADecorator.not_initialized)
        
        if hasattr(instance, '__post_init__'):
            instance.__post_init__()
        
        return instance

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
        return get_origin(type_) is list

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> None:
        value_type = get_args(type_)[0]
        table_name = f"list_{ClassInfo.get_semi_qual_name(value_type)}"
        if table_name not in setup_args.storage_engine.root_dict:
            setup_args.storage_engine.root_dict[table_name] = {}

    @classmethod
    def _merge(cls, merge_args: JSONMergeArgs, value: List[Any]) -> None:
        value_type = get_args(merge_args.type)[0]
        value_transcoder = merge_args.storage_engine.get_transcoder_type(value_type)
        table_name = f"list_{ClassInfo.get_semi_qual_name(value_type)}"
        
        list_id = cls._get_or_create_list_id(value)
        
        rows = []
        for index, item in enumerate(value):
            item_merge_args = merge_args.new(base_name='value', type=value_type)
            value_transcoder.merge(item_merge_args, item)
            
            row = {
                'index': index,
                **item_merge_args.encodes
            }
            rows.append(row)
        
        merge_args.root_dict[table_name][list_id] = rows

    @classmethod
    def _encode(cls, merge_args: JSONMergeArgs, value: List[Any]) -> None:
        list_id = cls._get_or_create_list_id(value)
        merge_args.encodes[f"{merge_args.base_name}_id"] = list_id

    @classmethod
    def decode(cls, decode_args: JSONDecodeArgs) -> List[Any]:
        return cls.create_lazy_instance(CFInstance(decode_args))

    @classmethod
    def create_lazy_instance(cls, cf_instance: CFInstance) -> List[Any]:
        lazy_list = []
        value_type = get_args(cf_instance.decode_args.type)[0]
        value_transcoder = cf_instance.decode_args.storage_engine.get_transcoder_type(value_type)
        table_name = f"list_{ClassInfo.get_semi_qual_name(value_type)}"
        list_id = cf_instance.decode_args.encodes[f"{cf_instance.decode_args.base_name}_id"]
        
        rows = cf_instance.decode_args.root_dict[table_name][list_id]
        rows.sort(key=lambda x: x['index'])
        
        for row in rows:
            item_decode_args = cf_instance.decode_args.new(
                encodes=row,
                base_name='value',
                type=value_type
            )
            lazy_list.append(value_transcoder.create_lazy_instance(CFInstance(item_decode_args)))
        
        return lazy_list

    @classmethod
    def _get_or_create_list_id(cls, value: List[Any]) -> str:
        if isinstance(value, InstrumentedList):
            return value._cf_instance.list_id
        list_id = cls.list_id_mapping.get(id(value), MISSING)
        if list_id is MISSING:
            list_id = str(uuid.uuid4())
            cls.list_id_mapping[id(value)] = list_id
        return list_id

    list_id_mapping: Dict[int, str] = {}

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