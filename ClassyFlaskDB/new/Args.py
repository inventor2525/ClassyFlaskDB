from dataclasses import dataclass, Field, field
from typing import Any, Dict, Optional, List, Union
from .ClassInfo import ClassInfo

@dataclass
class MergePath:
	parentObj: Optional['DataDecorator.Interface']
	fieldOnParent: Optional[Field]
	path: List[Union[str, int]] = field(default_factory=list)

@dataclass
class MergeArgs:
	context: Dict[str, Any]
	path: MergePath
	encodes: Dict[str, Any]
	is_dirty: Dict[int, bool]
	storage_engine: 'StorageEngine'

	def new(self, field: Field):
		return MergeArgs(
			context=self.context,
			path=MergePath(parentObj=self.path.parentObj, fieldOnParent=field),
			encodes=self.encodes,
			is_dirty=self.is_dirty,
			storage_engine=self.storage_engine
		)

@dataclass
class SetupArgs:
    storage_engine: 'StorageEngine'
    class_info: ClassInfo
	
@dataclass
class DecodeArgs:
    storage_engine: 'StorageEngine'
    parent: 'DataDecorator.Interface'
    field: Field
    path: List[Union[str, int]] = field(default_factory=list)