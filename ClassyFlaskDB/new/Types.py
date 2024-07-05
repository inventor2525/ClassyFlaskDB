from typing import List, Dict, Any, Union, TypeVar, Generic, Iterator, Mapping, Tuple
from .DirtyDecorator import *

class Interface(DirtyDecorator.Interface):
	pass
class ObjInterface(Interface, ):
	pass
BasicType = Union[bool,int,float,str]
ContextType = Dict[BasicType, Interface]