from enum import Enum

class ID_Type(Enum):
    USER_SUPPLIED = "user"
    UUID = "uuid"
    HASHID = "hashid"