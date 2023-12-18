from ClassyFlaskDB.DATA import *
from datetime import datetime
from typing import List, Dict

LoggerDATA = DATADecorator()

@LoggerDATA
class FileReference:
    name: str
    content_length: int
    file_path: str
    file_type: str

@LoggerDATA
class Entry:
    logger_name: str
    ip_address: str
    endpoint: str
    method: str
    timestamp: datetime
    files: List[FileReference] = field(default_factory=list)
    json_data: Dict = None

logger_engine = DATAEngine(LoggerDATA, engine_str='sqlite:///server_log.db')