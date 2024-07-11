from dataclasses import dataclass, Field
from typing import Any, Dict, Optional
from .Types import Interface, BasicType
from .ClassInfo import ClassInfo

@dataclass
class MergePath:
	parentObj: Optional[Interface]
	fieldOnParent: Optional[Field]

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