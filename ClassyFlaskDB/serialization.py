from pydub import AudioSegment
from io import BytesIO
from enum import Enum
from typing import Any, Type, Union, Callable
from dataclasses import dataclass

from datetime import datetime
from json import JSONEncoder

class JSONEncoder(JSONEncoder):
    rules = {}
    @staticmethod
    def add_formatting_rule(condition:Callable[[Any], bool], serializer:Callable[[Any],str]):
        JSONEncoder.rules[condition] = serializer
        
    def default(self, obj):
        if isinstance(obj, Enum):
            return f"<{type(obj).__name__}>.{obj.value}"
        if isinstance(obj, datetime):
            if obj.tzinfo is not None and obj.tzinfo.utcoffset(obj) is not None:
                return obj.strftime("%Y-%m-%d %H:%M:%S.%f %z")
            else:
                return obj.strftime("%Y-%m-%d %H:%M:%S.%f")
        for condition, serializer in JSONEncoder.rules.items():
            if condition(obj):
                return serializer(obj)
        return JSONEncoder.default(self, obj)
    
@dataclass
class BaseSerializer:
    as_file: bool = False
    mime_type: str = None
    
    def serialize(self, obj: Any) -> Union[dict, BytesIO]:
        return obj

    def deserialize(self, data: Union[dict, BytesIO]) -> Any:
        return data

class AudioSerializer(BaseSerializer):
    def __init__(self):
        super().__init__(as_file=True, mime_type='audio/wav')
    
    def serialize(self, obj: AudioSegment) -> BytesIO:
        buffer = BytesIO()
        obj.export(buffer, format="wav")
        buffer.seek(0)
        return buffer

    def deserialize(self, data: BytesIO) -> AudioSegment:
        return AudioSegment.from_file(data, format="wav")

class DATA_Serializer(BaseSerializer):
    def __init__(self, type:Type):
        super().__init__(as_file=False, mime_type='application/json')
        self.type = type
    
    def serialize(self, obj: Any) -> dict:
        return obj.to_json()

    def deserialize(self, data: dict) -> Any:
        return self.type.from_json(data)

type_serializer_mapping = {
        str: BaseSerializer(),
        int: BaseSerializer(),
        float: BaseSerializer(),
        bool: BaseSerializer(),
        AudioSegment: AudioSerializer()
    }

class TypeSerializationResolver:
    def __init__(self, type_serializer_mapping: dict = type_serializer_mapping):
        self.type_serializer_mapping = type_serializer_mapping
    
    def get(self, type: Type) -> BaseSerializer:
        if hasattr(type, 'from_json') and hasattr(type, 'to_json'):
            return DATA_Serializer(type)
        return self.type_serializer_mapping.get(type, BaseSerializer())