from pydub import AudioSegment
from io import BytesIO
from typing import Any, Type, Union
from dataclasses import dataclass

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
        super().__init__(as_file=True, mime_type='audio/mp3')
    
    def serialize(self, obj: AudioSegment) -> BytesIO:
        buffer = BytesIO()
        obj.export(buffer, format="wav")
        buffer.seek(0)
        return buffer

    def deserialize(self, data: BytesIO) -> AudioSegment:
        return AudioSegment.from_file(data, format="wav")

type_serializer_mapping = {
    str: BaseSerializer(),
    int: BaseSerializer(),
    float: BaseSerializer(),
    bool: BaseSerializer(),
    AudioSegment: AudioSerializer()
}