from .SQLStorageEngine import sql_transcoder_collection, String, Column
from .Args import MergeArgs, DecodeArgs, SetupArgs
from .Transcoder import Transcoder

from typing import Dict, Any, Type, List, Optional
from pydub import AudioSegment
import uuid
import os

@sql_transcoder_collection.add
class AudioTranscoder(Transcoder):
	audio_id_mapping: Dict[int, str] = {}
	
	@staticmethod
	def extension() -> Optional[str]:
		return "mp3"

	@classmethod
	def validate(cls, type_: Type) -> bool:
		return type_ == AudioSegment

	@classmethod
	def setup(cls, setup_args: SetupArgs, name: str, type_: Type, is_primary_key: bool) -> List[Column]:
		#TODO: Separate returns (somehow) for different StorageEngine types rather than making this the only method thats SQL specific.
		return [Column(f"{name}_id", String, primary_key=is_primary_key)]

	@classmethod
	def _encode(cls, merge_args: MergeArgs, value: AudioSegment) -> None:
		if merge_args.storage_engine.files_dir is None:
			raise ValueError("Cannot encode audio to the database without specifying files_dir")
		
		audio_id = merge_args.storage_engine.id_mapping.get(id(value), str(uuid.uuid4()))
		merge_args.storage_engine.id_mapping[id(value)] = audio_id

		file_path = os.path.join(merge_args.storage_engine.files_dir, f"{audio_id}.mp3")
		value.export(file_path, format="mp3")

		merge_args.encodes[f"{merge_args.base_name}_id"] = audio_id

	@classmethod
	def decode(cls, decode_args: DecodeArgs) -> AudioSegment:
		if decode_args.storage_engine.files_dir is None:
			raise ValueError("Cannot decode audio from the database without specifying files_dir")
		
		audio_id = decode_args.encodes.get(f"{decode_args.base_name}_id")
		if audio_id is None:
			return None

		file_path = os.path.join(decode_args.storage_engine.files_dir, f"{audio_id}.mp3")

		if audio_id in decode_args.storage_engine.id_mapping:
			return AudioSegment.from_mp3(file_path)

		audio = AudioSegment.from_mp3(file_path)
		decode_args.storage_engine.id_mapping[id(audio)] = audio_id
		return audio