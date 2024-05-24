from dataclasses import field, dataclass

from .DATADecorator import DATADecorator, ID_Type
from .DATAEngine import DATAEngine, Session

def print_DATA_json(json_data:dict) -> None:
	from ClassyFlaskDB.serialization import JSONEncoder
	import json
	print(json.dumps(json_data, indent=4, sort_keys=True, cls=JSONEncoder))