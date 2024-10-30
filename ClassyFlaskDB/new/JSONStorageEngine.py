from ClassyFlaskDB.new.StorageEngine import StorageEngine, StorageEngineQuery, TranscoderCollection
from ClassyFlaskDB.new.Transcoder import Transcoder, LazyLoadingTranscoder
from ClassyFlaskDB.new.Args import MergeArgs, SetupArgs, DecodeArgs, CFInstance
from ClassyFlaskDB.new.ClassInfo import ClassInfo, ID_Type
from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.InstrumentedList import InstrumentedList, ListCFInstance
from ClassyFlaskDB.new.InstrumentedDict import InstrumentedDict, DictCFInstance
from typing import Dict, Any, Type, List, Generic, TypeVar, Iterator, Optional, Union, Set, get_origin, get_args
from dataclasses import dataclass, field, MISSING
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import uuid

@dataclass
class JSONMergeArgs(MergeArgs):
    current_data: Dict[str, Any]  # Current JSON data being worked with
    root_path: Optional[Path] = None  # For folder-based storage

json_transcoder_collection = TranscoderCollection()

T = TypeVar('T')
class JSONStorageEngine(StorageEngine):
    def __init__(self, 
                storage_path: Optional[str] = None,
                initial_data: Optional[Dict[str, Any]] = None,
                use_folders: bool = False,
                data_decorator: 'DATADecorator' = None,
                extra_transcoders: List[Transcoder] = [],
                files_dir: Optional[str] = None):
        """
        Initialize JSONStorageEngine.
        
        Args:
            storage_path: Path to store JSON data (file or directory based on use_folders)
            initial_data: Initial data to populate the storage with
            use_folders: If True, use folder structure, else single JSON file
            data_decorator: DATADecorator instance for type registration
            extra_transcoders: Additional transcoders to use
            files_dir: Directory for storing binary files
        """
        super().__init__(files_dir=files_dir)
        self.use_folders = use_folders
        self.storage_path = Path(storage_path) if storage_path else None
        self._data = initial_data or {}
        self._extra_transcoders = extra_transcoders
        self.data_decorator = data_decorator
        self.transcoder_map = {}
        
        if self.data_decorator:
            self.data_decorator.finalize()
            self.setup(self.data_decorator)

        if storage_path:
            self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        if self.use_folders:
            self.storage_path.mkdir(parents=True, exist_ok=True)
        elif not self.storage_path.exists():
            with open(self.storage_path, 'w') as f:
                json.dump({}, f)
            
    @property
    def transcoders(self) -> Iterator[Transcoder]:
        for transcoder in self._extra_transcoders:
            yield transcoder
        for transcoder in json_transcoder_collection.transcoders:
            yield transcoder

    def setup(self, data_decorator: 'DATADecorator'):
        if self.use_folders:
            for cls in data_decorator.registry.values():
                class_info = ClassInfo.get(cls)
                table_path = self.storage_path / self.get_table_name(cls)
                table_path.mkdir(exist_ok=True)

    def merge(self, obj: Any, persist: bool = False):
        context = self.context if persist else {}
        current_data = self._data if not self.use_folders else {}
        
        merge_args = JSONMergeArgs(
            storage_engine=self,
            context=context,
            is_dirty={},
            encodes={},
            base_name='id',
            type=type(obj),
            current_data=current_data,
            root_path=self.storage_path if self.use_folders else None
        )
        
        transcoder = self.get_transcoder_type(type(obj))
        transcoder.merge(merge_args, obj)
        
        if self.use_folders:
            table_path = self.storage_path / self.get_table_name(type(obj))
            obj_path = table_path / f"{obj.get_primary_key()}.json"
            with open(obj_path, 'w') as f:
                json.dump(merge_args.encodes, f, indent=2)
        else:
            table_name = self.get_table_name(type(obj))
            if table_name not in self._data:
                self._data[table_name] = {}
            self._data[table_name][obj.get_primary_key()] = merge_args.encodes
            if self.storage_path:
                with open(self.storage_path, 'w') as f:
                    json.dump(self._data, f, indent=2)

    def get_table_name(self, cls: Type) -> str:
        class_info = ClassInfo.get(cls)
        return f"obj_{class_info.semi_qualname}"

    def get_transcoder_type(self, type_: Type) -> Type[Transcoder]:
        if type_ in self.transcoder_map:
            return self.transcoder_map[type_]
        for transcoder in self.transcoders:
            try:
                if transcoder.validate(type_):
                    self.transcoder_map[type_] = transcoder
                    return transcoder
            except:
                pass
        return None

    def query(self, cls: Type[T]) -> 'JSONStorageEngineQuery[T]':
        return JSONStorageEngineQuery(self, cls)

class JSONStorageEngineQuery(StorageEngineQuery[T]):
    def __init__(self, storage_engine: 'JSONStorageEngine', cls: Type[T]):
        self.storage_engine = storage_engine
        self.cls = cls
        self.transcoder = storage_engine.get_transcoder_type(cls)
        
        if not issubclass(self.transcoder, LazyLoadingTranscoder):
            raise ValueError(f"Transcoder for {cls} must support lazy loading")

    def _get_from_context(self, id_value: Any) -> Any:
        return self.storage_engine.context.get(self.cls, {}).get(id_value, MISSING)

    def filter_by_id(self, obj_id: Any) -> T:
        # Check context first
        context_obj = self._get_from_context(obj_id)
        if context_obj is not MISSING:
            return context_obj

        # Get data from storage
        table_name = self.storage_engine.get_table_name(self.cls)
        
        if self.storage_engine.use_folders:
            table_path = self.storage_engine.storage_path / table_name
            obj_path = table_path / f"{obj_id}.json"
            if not obj_path.exists():
                return None
            with open(obj_path) as f:
                encoded_values = json.load(f)
        else:
            if table_name not in self.storage_engine._data:
                return None
            if obj_id not in self.storage_engine._data[table_name]:
                return None
            encoded_values = self.storage_engine._data[table_name][obj_id]

        return self._create_lazy_instance(encoded_values)

    def first(self) -> T:
        table_name = self.storage_engine.get_table_name(self.cls)
        
        if self.storage_engine.use_folders:
            table_path = self.storage_engine.storage_path / table_name
            if not table_path.exists():
                return None
            try:
                first_file = next(table_path.glob("*.json"))
                with open(first_file) as f:
                    encoded_values = json.load(f)
                return self._create_lazy_instance(encoded_values)
            except StopIteration:
                return None
        else:
            if table_name not in self.storage_engine._data:
                return None
            try:
                obj_id = next(iter(self.storage_engine._data[table_name]))
                return self.filter_by_id(obj_id)
            except StopIteration:
                return None

    def all(self) -> Iterator[T]:
        table_name = self.storage_engine.get_table_name(self.cls)
        
        if self.storage_engine.use_folders:
            table_path = self.storage_engine.storage_path / table_name
            if not table_path.exists():
                return
            for file_path in table_path.glob("*.json"):
                with open(file_path) as f:
                    encoded_values = json.load(f)
                    yield self._create_lazy_instance(encoded_values)
        else:
            if table_name not in self.storage_engine._data:
                return
            for obj_id in self.storage_engine._data[table_name]:
                yield self.filter_by_id(obj_id)

    def _create_lazy_instance(self, encoded_values: Dict[str, Any]) -> T:
        class_info = ClassInfo.get(self.cls)
        instance = self.transcoder.create_lazy_instance(CFInstance(
            decode_args=DecodeArgs(
                storage_engine=self.storage_engine,
                encodes=encoded_values,
                base_name=None,
                type=self.cls
            ),
            unloaded_fields=set(class_info.fields.keys())
        ))
        
        # Add to context
        obj_id = encoded_values[class_info.primary_key_name]
        if self.cls not in self.storage_engine.context:
            self.storage_engine.context[self.cls] = {}
        self.storage_engine.context[self.cls][obj_id] = instance
        
        return instance

@json_transcoder_collection.add
class BasicsTranscoder(Transcoder):
    supported_types = {int, float, str, bool}

    @classmethod
    def validate(cls, type_: Type) -> bool:
        return type_ in cls.supported_types

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []  # No setup needed for JSON

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Any) -> None:
        merge_args.encodes[merge_args.base_name] = value

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Any:
        return decode_args.type(decode_args.encodes[decode_args.base_name])

@json_transcoder_collection.add
class ObjectTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return ClassInfo.has_ClassInfo(type_)

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []  # No setup needed for JSON

    @classmethod
    def _merge(cls, merge_args: MergeArgs, obj: Any) -> None:
        if obj is None:
            return

        personal_merge_args = merge_args.new(
            same_depth=True,
            encodes={}
        )

        class_info = ClassInfo.get(type(obj))
        
        cf_instance = CFInstance.get(obj)
        for field in class_info.fields.values():
            if cf_instance is not MISSING:
                if field.name in cf_instance.unloaded_fields:
                    continue
            
            value = getattr(obj, field.name)
            transcoder = personal_merge_args.storage_engine.get_transcoder_type(field.type)
            field_merge_args = personal_merge_args.new(
                base_name=field.name,
                type=field.type
            )
            transcoder.merge(field_merge_args, value)

        # Handle JSON storage engine specific logic
        if isinstance(merge_args, JSONMergeArgs):
            table_name = merge_args.storage_engine.get_table_name(type(obj))
            if merge_args.root_path:
                # Folder-based storage
                obj_path = merge_args.root_path / table_name / f"{obj.get_primary_key()}.json"
                obj_path.parent.mkdir(exist_ok=True)
                with open(obj_path, 'w') as f:
                    json.dump(personal_merge_args.encodes, f, indent=2)
            else:
                # Dictionary-based storage
                if table_name not in merge_args.current_data:
                    merge_args.current_data[table_name] = {}
                merge_args.current_data[table_name][obj.get_primary_key()] = personal_merge_args.encodes

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Any) -> None:
        if value is None:
            merge_args.encodes[f"{merge_args.base_name}_id"] = None
            merge_args.encodes[f"{merge_args.base_name}_type"] = None
            return

        class_info = ClassInfo.get(type(value))
        merge_args.encodes[f"{merge_args.base_name}_id"] = value.get_primary_key()
        merge_args.encodes[f"{merge_args.base_name}_type"] = class_info.semi_qualname

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Any:
        id_value = decode_args.encodes[f"{decode_args.base_name}_id"]
        type_name = decode_args.encodes[f"{decode_args.base_name}_type"]
        
        if id_value is None or type_name is None:
            return None

        obj_type = decode_args.storage_engine.data_decorator.registry[type_name]
        return decode_args.storage_engine.query(obj_type).filter_by_id(id_value)

    @classmethod
    def create_lazy_instance(cls, cf_instance: CFInstance) -> Any:
        instance = object.__new__(cf_instance.decode_args.type)
        setattr(instance, '_cf_instance', cf_instance)
        
        class_info = ClassInfo.get(cf_instance.decode_args.type)
        
        for field_name in class_info.fields:
            setattr(instance, field_name, DATADecorator.not_initialized)
        
        for field in class_info.all_fields:
            if field.name not in class_info.fields:
                if field.default is not MISSING:
                    setattr(instance, field.name, field.default)
                elif field.default_factory is not MISSING:
                    setattr(instance, field.name, field.default_factory())
        
        if hasattr(instance, '__post_init__'):
            instance.__post_init__()
        
        object.__setattr__(instance, '__custom_setter_enabled__', True)
        return instance

@json_transcoder_collection.add
class DateTimeTranscoder(Transcoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return type_ == datetime

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: datetime) -> None:
        if value is None:
            merge_args.encodes[merge_args.base_name] = None
            return
            
        tz_str = value.tzinfo.key if value.tzinfo else None
        merge_args.encodes[merge_args.base_name] = {
            'timestamp': value.timestamp(),
            'timezone': tz_str
        }

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> datetime:
        value = decode_args.encodes[decode_args.base_name]
        if value is None:
            return None
            
        dt = datetime.fromtimestamp(value['timestamp'])
        if value['timezone']:
            dt = dt.replace(tzinfo=ZoneInfo(value['timezone']))
        return dt

@json_transcoder_collection.add
class EnumTranscoder(Transcoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return isinstance(type_, type) and issubclass(type_, Enum)

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Enum) -> None:
        merge_args.encodes[merge_args.base_name] = value.name if value else None

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Enum:
        value = decode_args.encodes[decode_args.base_name]
        return decode_args.type[value] if value is not None else None

@json_transcoder_collection.add
class ListTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return get_origin(type_) is list

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []

    @classmethod
    def _merge(cls, merge_args: MergeArgs, value: List[Any]) -> None:
        if value is None:
            return
        
        value_type = get_args(merge_args.type)[0]
        value_transcoder = merge_args.storage_engine.get_transcoder_type(value_type)
        
        encoded_items = []
        for index, item in enumerate(value):
            item_merge_args = merge_args.new(
                same_depth=True,
                encodes={},
                base_name='value',
                type=value_type
            )
            value_transcoder.merge(item_merge_args, item)
            encoded_items.append({
                'index': index,
                **item_merge_args.encodes
            })
        
        merge_args.encodes[f"{merge_args.base_name}_items"] = encoded_items

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> InstrumentedList:
        value_type = get_args(decode_args.type)[0]
        value_transcoder = decode_args.storage_engine.get_transcoder_type(value_type)
        
        encoded_items = decode_args.encodes.get(f"{decode_args.base_name}_items", [])
        
        return cls.create_lazy_instance(ListCFInstance(
            decode_args=decode_args.new(
                encodes=encoded_items
            ),
            list_id=str(uuid.uuid4()),  # Generate a new ID for the list
            value_type=value_type,
            value_transcoder=value_transcoder
        ))

    @classmethod
    def create_lazy_instance(cls, cf_instance: ListCFInstance) -> InstrumentedList:
        lazy_list = InstrumentedList()
        lazy_list._cf_instance = cf_instance
        lazy_list.extend([MISSING for _ in range(len(cf_instance.decode_args.encodes))])
        return lazy_list

@json_transcoder_collection.add
class DictionaryTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return get_origin(type_) is dict

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []

    @classmethod
    def _merge(cls, merge_args: MergeArgs, value: Dict[Any, Any]) -> None:
        if value is None:
            return
        
        key_type, value_type = get_args(merge_args.type)
        key_transcoder = merge_args.storage_engine.get_transcoder_type(key_type)
        value_transcoder = merge_args.storage_engine.get_transcoder_type(value_type)
        
        encoded_items = []
        for key, item in value.items():
            key_merge_args = merge_args.new(
                same_depth=True,
                encodes={},
                base_name='key',
                type=key_type
            )
            value_merge_args = merge_args.new(
                same_depth=True,
                encodes={},
                base_name='value',
                type=value_type
            )
            
            key_transcoder.merge(key_merge_args, key)
            value_transcoder.merge(value_merge_args, item)
            
            encoded_items.append({
                **key_merge_args.encodes,
                **value_merge_args.encodes
            })
        
        merge_args.encodes[f"{merge_args.base_name}_items"] = encoded_items

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> InstrumentedDict:
        key_type, value_type = get_args(decode_args.type)
        key_transcoder = decode_args.storage_engine.get_transcoder_type(key_type)
        value_transcoder = decode_args.storage_engine.get_transcoder_type(value_type)
        
        encoded_items = decode_args.encodes.get(f"{decode_args.base_name}_items", [])
        
        return cls.create_lazy_instance(DictCFInstance(
            decode_args=decode_args.new(
                encodes=encoded_items
            ),
            dict_id=str(uuid.uuid4()),
            key_transcoder=key_transcoder,
            value_transcoder=value_transcoder
        ))

@json_transcoder_collection.add
class JsonDictTranscoder(Transcoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        origin = get_origin(type_)
        if origin is not dict:
            return False
        
        key_type, value_type = get_args(type_)
        # Check if both key and value types are JSON serializable
        return (key_type in (str, int, float) and 
                value_type in (str, int, float, bool, None))

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []

    @classmethod
    def _encode(cls, merge_args: MergeArgs, value: Dict[Any, Any]) -> None:
        merge_args.encodes[merge_args.base_name] = value

    @classmethod
    def decode(cls, decode_args: DecodeArgs) -> Dict[Any, Any]:
        return decode_args.encodes[decode_args.base_name]