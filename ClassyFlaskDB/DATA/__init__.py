from sqlalchemy.orm import Session
from dataclasses import field

from .DATADecorator import DATADecorator, ID_Type
from .DATAEngine import DATAEngine

def print_DATA_json(json_data:dict) -> None:
	from ClassyFlaskDB.Flaskify.serialization import FlaskifyJSONEncoder
	import json
	print(json.dumps(json_data, indent=4, sort_keys=True, cls=FlaskifyJSONEncoder))