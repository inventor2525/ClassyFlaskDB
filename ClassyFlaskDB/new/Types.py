from typing import List, Dict, Any, Union, TypeVar, Generic, Iterator

class Interface:
	pass
BasicType = Union[bool,int,float,str]
ContextType = Dict[BasicType, Interface]