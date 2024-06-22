from typing import List, Dict, Any, Union
from dataclasses import dataclass, Field, field

BasicType = Union[bool,int,float,str]

@dataclass
class MergePath:
	parentObj:objects_new_methods
	fieldOnParent:Field
	otherPath:List[BasicType] = field(default_factory=list)
	
	def new(self, path_element:BasicType):
		path = list(self.otherPath)
		path.append(path_element)
		return MergePath(self.parentObj, self.fieldOnParent, path)
		
	def __str__(self):
		fieldStr = "" if self.fieldOnParent is None else self.fieldOnParent.name
		if self.parentObj is None:
			path = fieldStr
		else:
			path = f"{self.parentObj.get_primary_key()}.{fieldStr}"
		if len(self.otherPath)==0:
			return path
		
		inner = ">.<".join(self.otherPath)
		return f"{path}.<{inner}>"
	
@dataclass
class MergeArgs:
	context:Dict[BasicType, objects_new_methods]
	path:MergePath
	encodes:Dict[str, Any]
	is_dirty:dict
	
	def new(self, path_element:BasicType, encodes:Any):
		return MergeArgs(self.context, self.path.new(path_element), encodes, self.is_dirty)