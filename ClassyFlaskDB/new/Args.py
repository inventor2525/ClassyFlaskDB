from dataclasses import dataclass, Field
from typing import Any, Dict, Optional
from .Types import Interface, BasicType

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

	def new(self, field: Field, new_encodes: Dict[str, Any]):
		return MergeArgs(
			context=self.context,
			path=MergePath(parentObj=self.path.parentObj, fieldOnParent=field),
			encodes=new_encodes,
			is_dirty=self.is_dirty,
			storage_engine=self.storage_engine
		)