from ClassyFlaskDB.new.StorageEngine import StorageEngine, StorageEngineQuery, TranscoderCollection
from ClassyFlaskDB.new.Transcoder import Transcoder, LazyLoadingTranscoder
from ClassyFlaskDB.new.Args import MergeArgs, SetupArgs, DecodeArgs, CFInstance
from ClassyFlaskDB.new.ClassInfo import ClassInfo, ID_Type
from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.InstrumentedList import InstrumentedList, ListCFInstance
from ClassyFlaskDB.new.InstrumentedDict import InstrumentedDict, DictCFInstance
from typing import Dict, Any, Type, List, Generic, TypeVar, Iterator, Optional, Union, Set, get_origin, get_args, Iterable
from dataclasses import dataclass, field, MISSING, Field
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import uuid

json_transcoder_collection = TranscoderCollection()

T = TypeVar('T')
class JSONStorageEngine(StorageEngine):
    def __init__(self, 
                storage_path: Optional[str] = None,
                initial_data: Optional[Dict[str, Any]] = None,
                use_folders: bool = False,
                data_decorator: 'DATADecorator' = None,
                extra_transcoders: List[Transcoder] = [],
                files_dir: Optional[str] = None,
                group_names:Optional[Iterable[str]]=None):
        """
        Initialize JSONStorageEngine.
        
        Args:
            storage_path: Path to store JSON data (file or directory based on use_folders)
            initial_data: Initial data to populate the storage with
            use_folders: If True, use folder structure, else single JSON file
            data_decorator: DATADecorator instance for type registration
            extra_transcoders: Additional transcoders to use
            files_dir: Directory for storing binary files
            group_names: Used to specify which class groups from DATADecorator to use.
        """
        super().__init__(data_decorator, files_dir=files_dir, group_names=group_names)
        self.use_folders = use_folders
        self.storage_path = Path(storage_path) if storage_path else None
        
        self._data:Dict[str,Dict[str,Union[dict,list]]] = {}
        if initial_data:
            self._data = initial_data
        if storage_path:
            self._ensure_storage_exists()
            if not use_folders:
                with open(self.storage_path, 'r') as f:
                    self._data.update(json.load(f))
        
        self._extra_transcoders = extra_transcoders
        self.data_decorator = data_decorator
        self.transcoder_map = {}
        
        if self.data_decorator:
            self.data_decorator.finalize()
            self.setup()

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
        
        if self.storage_path and not self.use_folders:
            with open(self.storage_path, 'w') as f:
                json.dump(self._data, f, indent=4)
    
    def _single_value_path(self, table_name:str, value_id:str) -> Path:
        table_path = self.storage_path / table_name
        table_path.mkdir(parents=True, exist_ok=True)
        return table_path / f"{value_id}.json"
    
    def _iter_keys_in_table(self, table_name:str) -> Iterator[str]:
        mem_table = self._data.get(table_name, {})
        for key in mem_table.keys():
            yield key
            
        if self.storage_path and self.use_folders:
            table_path = self.storage_path / table_name
            if table_path.exists():
                for file_path in table_path.glob("*.json"):
                    value_id = file_path.stem
                    if value_id not in mem_table:
                        yield value_id
    
    def _save_value_encodes(self, table_name:str, value_id:str, encodes:Union[dict,list]):
        if table_name not in self._data:
            self._data[table_name] = {}
        self._data[table_name][value_id] = encodes
        
        if self.storage_path and self.use_folders:
            value_path = self._single_value_path(table_name,value_id)
            with open(value_path, 'w') as f:
                json.dump(encodes, f, indent=2)
    
    def _get_value_encodes(self, table_name:str, value_id:str, default:Any=MISSING) -> Union[dict,list]:
        try:
            return self._data[table_name][value_id]
        except:
            if self.storage_path and self.use_folders:
                value_path = self._single_value_path(table_name,value_id)
                with open(value_path, 'r') as f:
                    encodes = json.load(f)
                    if table_name not in self._data:
                        self._data[table_name] = {}
                    self._data[table_name][value_id] = encodes
                    return encodes
            if default == MISSING:
                raise KeyError(f"value id '{value_id}' not found in json table '{table_name}'")
        return default
            
    def get_transcoder_type(self, type_: Type, field_:Optional[Field]=None) -> Type[Transcoder]:
        try:
            return field_.metadata['transcoder']
        except:
            pass
        
        if type_ in self.transcoder_map:
            return self.transcoder_map[type_]
        for transcoder in self.transcoders:
            try:
                if transcoder.validate(type_):
                    print(f"Transcoder for {type_} is: {transcoder}")
                    self.transcoder_map[type_] = transcoder
                    return transcoder
            except Exception as e:
                print(f"Transcoder validate {type_} error {e}")
        return None

    def query(self, cls: Type[T]) -> 'JSONStorageEngineQuery[T]':
        return JSONStorageEngineQuery(self, cls)

@dataclass
class JSONMergeArgs(MergeArgs):
    storage_engine: JSONStorageEngine = field(kw_only=True)
    current_data: Dict[str, Any]  # Current JSON data being worked with
    root_path: Optional[Path] = None  # For folder-based storage
    
@dataclass
class JSONDecodeArgs(DecodeArgs):
    storage_engine: JSONStorageEngine = field(kw_only=True)
    
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
        table_name = ObjectTranscoder.get_table_name(self.cls)
        encoded_values = self.storage_engine._get_value_encodes(table_name, obj_id)
        return self._create_lazy_instance(encoded_values)

    def first(self) -> T:
        table_name = ObjectTranscoder.get_table_name(self.cls)
        for obj_id in self.storage_engine._iter_keys_in_table(table_name):
            return self.filter_by_id(obj_id)
        return None

    def all(self) -> Iterator[T]:
        table_name = ObjectTranscoder.get_table_name(self.cls)
        for obj_id in self.storage_engine._iter_keys_in_table(table_name):
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
    def _encode(cls, merge_args: JSONMergeArgs, value: Any) -> None:
        merge_args.encodes[merge_args.base_name] = value

    @classmethod
    def decode(cls, decode_args: JSONDecodeArgs) -> Any:
        return decode_args.type(decode_args.encodes[decode_args.base_name])

@json_transcoder_collection.add
class ObjectTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        return ClassInfo.has_ClassInfo(type_)
    
    @classmethod
    def get_table_name(cls, type_: Type) -> str:
        class_info = ClassInfo.get(type_)
        return f"obj_{class_info.semi_qualname}"
    
    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []  # No setup needed for JSON

    @classmethod
    def _merge(cls, merge_args: JSONMergeArgs, obj: Any) -> None:
        if obj is None:
            return

        class_info = ClassInfo.get(type(obj))
        
        obj_encodes = {}
        cf_instance = CFInstance.get(obj)
        for field in class_info.fields.values():
            if cf_instance is not MISSING and cf_instance.decode_args.storage_engine is merge_args.storage_engine:
                if field.name in cf_instance.unloaded_fields:
                    continue
            
            value = getattr(obj, field.name)
            transcoder = merge_args.storage_engine.get_transcoder_type(field.type, field)
            field_merge_args = merge_args.new(
                base_name=field.name,
                type=field.type,
                encodes=obj_encodes
            )
            transcoder.merge(field_merge_args, value)
        
        merge_args.storage_engine._save_value_encodes(
            ObjectTranscoder.get_table_name(type(obj)),
            obj.get_primary_key(),
            obj_encodes
        )

    @classmethod
    def _encode(cls, merge_args: JSONMergeArgs, value: Any) -> None:
        if value is None:
            merge_args.encodes[f"{merge_args.base_name}_id"] = None
            merge_args.encodes[f"{merge_args.base_name}_type"] = None
            return

        class_info = ClassInfo.get(type(value))
        merge_args.encodes[f"{merge_args.base_name}_id"] = value.get_primary_key()
        merge_args.encodes[f"{merge_args.base_name}_type"] = class_info.semi_qualname

    @classmethod
    def decode(cls, decode_args: JSONDecodeArgs) -> Any:
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
    def _encode(cls, merge_args: JSONMergeArgs, value: datetime) -> None:
        if value is None:
            merge_args.encodes[merge_args.base_name] = None
            return
            
        tz_str = value.tzinfo.key if value.tzinfo else None
        merge_args.encodes[merge_args.base_name] = {
            'timestamp': value.astimezone(ZoneInfo("UTC")).timestamp(),  # Convert to UTC first
            'timezone': tz_str
        }

    @classmethod
    def decode(cls, decode_args: JSONDecodeArgs) -> datetime:
        value = decode_args.encodes[decode_args.base_name]
        if value is None:
            return None
            
        dt = datetime.fromtimestamp(value['timestamp'], ZoneInfo("UTC"))
        if value['timezone']:
            dt = dt.astimezone(ZoneInfo(value['timezone']))
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
    def _encode(cls, merge_args: JSONMergeArgs, value: Enum) -> None:
        merge_args.encodes[merge_args.base_name] = value.name if value else None

    @classmethod
    def decode(cls, decode_args: JSONDecodeArgs) -> Enum:
        value = decode_args.encodes[decode_args.base_name]
        return decode_args.type[value] if value is not None else None

@json_transcoder_collection.add
class ListTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        origin = get_origin(type_)
        if origin is not list:
            return False
            
        def check_type(t: Type, seen: Set[Type] = None) -> bool:
            if seen is None:
                seen = set()
            
            if t in seen:
                return False
            seen.add(t)
            
            # Simplified validation: check if it's a basic type or DATA object
            if ClassInfo.has_ClassInfo(t):
                return True
                
            origin = get_origin(t)
            if origin is None:
                return BasicsTranscoder.validate(t)
                
            if origin is list:
                value_type = get_args(t)[0]
                return check_type(value_type, seen)
                
            if origin is dict:
                key_type, value_type = get_args(t)
                return (check_type(key_type, seen) and 
                       check_type(value_type, seen))
            
            return False
            
        value_type = get_args(type_)[0]
        return check_type(value_type)
    
    @classmethod
    def get_table_name(cls, type__: Type) -> str:
        value_type = get_args(type__)[0]
        origin = get_origin(value_type)
        return f"list_{origin.__name__ if origin else value_type.__name__}"

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []

    @classmethod
    def _merge(cls, merge_args: JSONMergeArgs, value: List[Any]) -> None:
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
        
        merge_args.storage_engine._save_value_encodes(
            cls.get_table_name(merge_args.type),
            StorageEngine.get_id(value),
            encoded_items
        )
        
    @classmethod
    def _encode(cls, merge_args: JSONMergeArgs, value: List[Any]) -> None:
        list_id = StorageEngine.get_id(value)
        merge_args.encodes[f"{merge_args.base_name}_id"] = list_id

    @classmethod
    def decode(cls, decode_args: JSONDecodeArgs) -> InstrumentedList:
        value_type = get_args(decode_args.type)[0]
        value_transcoder = decode_args.storage_engine.get_transcoder_type(value_type)
        
        list_id = decode_args.encodes[f"{decode_args.base_name}_id"]
        
        encoded_items = decode_args.storage_engine._get_value_encodes(
            cls.get_table_name(decode_args.type),
            list_id, default=[]
        )
        
        return cls.create_lazy_instance(ListCFInstance(
            decode_args=decode_args.new(
                encodes=encoded_items
            ),
            list_id=list_id,  # Generate a new ID for the list
            value_type=value_type,
            value_transcoder=value_transcoder
        ))

    @classmethod
    def create_lazy_instance(cls, cf_instance: ListCFInstance) -> InstrumentedList:
        return InstrumentedList.from_cf_instance(cf_instance)

@json_transcoder_collection.add
class JsonDictTranscoder(Transcoder):
    @classmethod
    def is_json_primitive(cls, type_: Type) -> bool:
        return type_ in (str, int, float, bool, type(None))

    @classmethod
    def _validate_type(cls, type_: Type, seen: Set[Type] = None) -> bool:
        if seen is None:
            seen = set()
        
        if type_ in seen:
            return False
        seen.add(type_)

        origin = get_origin(type_)
        if origin is None:
            return cls.is_json_primitive(type_)
        
        if origin is list:
            value_type = get_args(type_)[0]
            return cls._validate_type(value_type, seen)
        
        if origin is dict:
            key_type, value_type = get_args(type_)
            if key_type is str and value_type is Any:
                return True
            return (cls.is_json_primitive(key_type) and 
                   cls._validate_type(value_type, seen))
        
        return False

    @classmethod
    def validate(cls, type_: Type) -> bool:
        if type_ is dict:
            return True
        origin = get_origin(type_)
        if origin is not dict:
            return False
        
        key_type, value_type = get_args(type_)
        return cls._validate_type(type_)

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []

    @classmethod
    def _encode(cls, merge_args: JSONMergeArgs, value: Dict[Any, Any]) -> None:
        if value is None:
            merge_args.encodes[merge_args.base_name] = None
            return
        merge_args.encodes[merge_args.base_name] = dict(value)  # Create a copy of the dictionary

    @classmethod
    def decode(cls, decode_args: JSONDecodeArgs) -> Dict[Any, Any]:
        value = decode_args.encodes[decode_args.base_name]
        return dict(value) if value is not None else None
    
@json_transcoder_collection.add
class DictionaryTranscoder(LazyLoadingTranscoder):
    @classmethod
    def validate(cls, type_: Type) -> bool:
        origin = get_origin(type_)
        if origin is not dict:
            return False
            
        def check_type(t: Type, seen: Set[Type] = None) -> bool:
            if seen is None:
                seen = set()
                
            if t in seen:
                return False
            seen.add(t)
            
            if ClassInfo.has_ClassInfo(t):
                return True
                
            origin = get_origin(t)
            if origin is None:
                return BasicsTranscoder.validate(t)
                
            if origin is list:
                value_type = get_args(t)[0]
                return check_type(value_type, seen)
                
            if origin is dict:
                key_type, value_type = get_args(t)
                return (check_type(key_type, seen) and 
                       check_type(value_type, seen))
            
            return False
            
        key_type, value_type = get_args(type_)
        return check_type(key_type) and check_type(value_type)
    
    @classmethod
    def get_table_name(cls, type_) -> str:
        key_type, value_type = get_args(type_)
        return f"dict_{key_type.__name__}_{value_type.__name__}"

    @classmethod
    def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Any]:
        return []

    @classmethod
    def _merge(cls, merge_args: JSONMergeArgs, value: Dict[Any, Any]) -> None:
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
        
        merge_args.storage_engine._save_value_encodes(
            cls.get_table_name(merge_args.type),
            StorageEngine.get_id(value),
            encoded_items
        )
    
    @classmethod
    def _encode(cls, merge_args: JSONMergeArgs, value: Dict[Any, Any]) -> None:
        dict_id = StorageEngine.get_id(value)
        merge_args.encodes[f"{merge_args.base_name}_id"] = dict_id
        
    @classmethod
    def decode(cls, decode_args: JSONDecodeArgs) -> InstrumentedDict:
        key_type, value_type = get_args(decode_args.type)
        key_transcoder = decode_args.storage_engine.get_transcoder_type(key_type)
        value_transcoder = decode_args.storage_engine.get_transcoder_type(value_type)
        
        # Get the dict's ID and items
        dict_id = decode_args.encodes.get(f"{decode_args.base_name}_id")
        items = decode_args.storage_engine._get_value_encodes(
            cls.get_table_name(decode_args.type),
            dict_id, default={}
        )
        
        # Create new decode args with just the items
        items_decode_args = decode_args.new(
            encodes=items
        )
        
        return InstrumentedDict.from_cf_instance(DictCFInstance(
            decode_args=items_decode_args,
            dict_id=dict_id,
            key_transcoder=key_transcoder,
            value_transcoder=value_transcoder
        ))
    
    @classmethod
    def create_lazy_instance(cls, cf_instance: DictCFInstance) -> InstrumentedDict:
        return InstrumentedDict.from_cf_instance(cf_instance)