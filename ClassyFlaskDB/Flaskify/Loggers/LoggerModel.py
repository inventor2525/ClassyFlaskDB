from ClassyFlaskDB.DefaultModel import *
from datetime import datetime
from typing import List, Dict

@DATA
@dataclass
class FileReference:
    name: str
    content_length: int
    file_path: str
    file_type: str

@DATA
@dataclass
class Entry:
    logger_name: str
    ip_address: str
    endpoint: str
    method: str
    timestamp: datetime
    files: List[FileReference] = field(default_factory=list)
    json_data: Dict = None