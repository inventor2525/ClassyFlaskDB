from sqlalchemy.orm import registry, joinedload, class_mapper
from sqlalchemy.orm.collections import InstrumentedList

from ClassyFlaskDB.helpers.Decorators.LazyDecorator import LazyDecorator
from ClassyFlaskDB.helpers.Decorators.capture_field_info import capture_field_info
from ClassyFlaskDB.helpers.resolve_type import TypeResolver
from ClassyFlaskDB.helpers.Decorators.AnyParam import AnyParam
from ClassyFlaskDB.DATA.DATAEngine import DATAEngine
from ClassyFlaskDB.helpers.Decorators.to_sql import to_sql
from ClassyFlaskDB.DATA.ID_Type import ID_Type

from dataclasses import dataclass
from copy import deepcopy

from typing import Any, Dict, Iterable, List, Type
import uuid

class DATADecorator(AnyParam):
    def __init__(self, *args, **kwargs):
        # Initialize any state or pass any parameters required
        self.args = args
        self.kwargs = kwargs
        self.lazy = LazyDecorator()
        self.decorated_classes = {}
        self.mapper_registry = registry()
        TypeResolver.append_globals(globals())
        
        self._finalized = False
    
    def finalize(self, globals_return:Dict[str, Any]=None) -> None:
        if globals_return:
            TypeResolver.append_globals(globals_return)
        TypeResolver.append_globals(self.decorated_classes)
        
        self.lazy["default"](self.mapper_registry)
        self.lazy.clear_group("default")
        self._finalized = True
    
    def decorate(self, cls:Type[Any], generated_id_type:ID_Type=ID_Type.UUID, hashed_fields:List[str]=None, excluded_fields:Iterable[str]=[], included_fields:Iterable[str]=[], auto_include_fields=True, exclude_prefix:str="_") -> Type[Any]:
        lazy_decorators = []
        self.decorated_classes[cls.__name__] = cls

        cls = dataclass(cls)
        cls = capture_field_info(cls, excluded_fields=excluded_fields, included_fields=included_fields, auto_include_fields=auto_include_fields, exclude_prefix=exclude_prefix)
        if cls.FieldsInfo.primary_key_name is None:
            def add_pk(pk_name:str, pk_type:Type):
                setattr(cls, pk_name, None)
                cls.__annotations__[pk_name] = pk_type
                
                cls.FieldsInfo.primary_key_name = pk_name
                if pk_name not in cls.FieldsInfo.field_names:
                    cls.FieldsInfo.field_names.append(pk_name)
                    
                if cls.FieldsInfo.type_hints is not None:
                    cls.FieldsInfo.type_hints[pk_name] = pk_type
            
            if generated_id_type == ID_Type.UUID:
                def new_id(self):
                    self.auto_id = str(uuid.uuid4())
                setattr(cls, "new_id", new_id)
                add_pk("auto_id", str)
                
            elif generated_id_type == ID_Type.HASHID:
                import hashlib
                
                if hashed_fields is None:
                    hashed_fields = deepcopy(cls.FieldsInfo.field_names)
                
                def get_hash_field_getters(cls: Type) -> Type:
                    field_getters = {}
                    for field_name in hashed_fields:
                        hashed_field_type = cls.FieldsInfo.get_field_type(field_name)
                        
                        if getattr(hashed_field_type, "FieldsInfo", None) is not None:
                            def field_getter(self, field_name:str):
                                obj = getattr(self, field_name)
                                if obj is None:
                                    return ""
                                return str(obj.get_primary_key())
                            field_getters[field_name] = field_getter
                        elif hasattr(hashed_field_type, "__origin__") and hashed_field_type.__origin__ in [list, tuple]:
                            list_type = hashed_field_type.__args__[0]
                            if getattr(list_type, "FieldsInfo", None) is not None:
                                def field_getter(self, field_name:str):
                                    l = getattr(self, field_name)
                                    if l is None:
                                        return "[]"
                                    l_str = ",".join([str(None if item is None else item.get_primary_key()) for item in l])
                                    return f"[{l_str}]"
                                field_getters[field_name] = field_getter
                            else:
                                def field_getter(self, field_name:str):
                                    return str(getattr(self, field_name))
                                field_getters[field_name] = field_getter
                        else:
                            def field_getter(self, field_name:str):
                                return str(getattr(self, field_name))
                            field_getters[field_name] = field_getter
                    cls.__field_getters__ = field_getters
                    return cls
                    
                lazy_decorators.append(get_hash_field_getters)
                
                supplied_new_id = getattr(cls, "new_id", None)
                def new_id(self) -> str:
                    try:
                        if supplied_new_id is not None:
                            supplied_new_id(self)
                        fields = [cls.__field_getters__[field_name](self,field_name) for field_name in hashed_fields]
                        self.auto_id = hashlib.sha256(",".join(fields).encode("utf-8")).hexdigest()
                    except:
                        self.auto_id = f"hash id failed {str(uuid.uuid4())}"
                setattr(cls, "new_id", new_id)
                add_pk("auto_id", str)
            
            init = cls.__init__
            def __init__(self, *args, **kwargs):
                init(self, *args, **kwargs)
                self.new_id()
            setattr(cls, "__init__", __init__)
                
        def get_primary_key(self):
            return getattr(self, cls.FieldsInfo.primary_key_name)
        setattr(cls, "get_primary_key", get_primary_key)
        
        cls = self.lazy([to_sql(), *lazy_decorators])(cls)
    
        # Define a custom __deepcopy__ method
        def __deepcopy__(self, memo):
            if id(self) in memo:
                return memo[id(self)]
            
            mapper = class_mapper(self.__class__)
            cls_copy = mapper.class_manager.new_instance()
            # cls_copy = self.__class__()
            memo[id(self)] = cls_copy
            
            def fields(cls):
                for field_name in cls.FieldsInfo.field_names:
                    yield field_name
                if hasattr(cls, "__cls_type__"):
                    yield "__cls_type__"

            for field_name in fields(cls):
                value = getattr(self, field_name, None)
                if value is not None:
                    if isinstance(value, InstrumentedList):
                        setattr(cls_copy, field_name, deepcopy(list(value), memo))
                    # elif isinstance(value, dict):
                    #     setattr(cls_copy, field_name, deepcopy(value, memo))
                    else:
                        try:
                            setattr(cls_copy, field_name, deepcopy(value, memo))
                        except:
                            setattr(cls_copy, field_name, None)
            
            return cls_copy

        # Attach the custom __deepcopy__ method to the class
        setattr(cls, '__deepcopy__', __deepcopy__)
        
        def to_json(cls_self):
            engine = DATAEngine(self)
            
            obj = deepcopy(cls_self)
            
            engine.merge(obj)

            json_data = engine.to_json()
            engine.dispose()
            
            return {
                "primary_key":obj.get_primary_key(),
                "type":type(obj).__name__,
                "obj":json_data
            }
            
        @staticmethod
        def from_json(json_data:dict):
            engine = DATAEngine(self)
            engine.insert_json(json_data["obj"])
            
            pk_col = cls.__table__.c[cls.FieldsInfo.primary_key_name]
            with engine.session() as session:
                objs = deepcopy( session.query(cls).options(joinedload('*')).filter(pk_col==json_data["primary_key"]).first() )
                
            engine.dispose()
            return objs
            
        setattr(cls, "to_json", to_json)
        setattr(cls, "from_json", from_json)
        return cls