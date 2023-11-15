from sqlalchemy import Table, Column, String, Integer, ForeignKey, DateTime, JSON, Enum, Boolean, Float, Text
from sqlalchemy.orm import declarative_base, relationship, registry
from sqlalchemy.ext.declarative import declared_attr, DeclarativeMeta
from datetime import datetime
from ClassyFlaskDB.capture_field_info import FieldInfo

from ClassyFlaskDB.helpers import *

type_map = {
	bool: Boolean,
	int: Integer,
	float: Float,
	str: Text,
	
	datetime: DateTime
}
def type_table_name(cls):
	return f"{cls.__name__}_Table"

class GetterSetter:
	def __init__(self, field_info:FieldInfo):
		self.field_info = field_info
		self.columns :List[Column] = []
		self.relationships :Dict[str,relationship] = {}

class SimpleOneToOne(GetterSetter):
	def __init__(self, field_info:FieldInfo, column:Column):
		super().__init__(field_info)

		column.name = self.field_info.field_name
		self.columns = [column]

class OneToOneReference(GetterSetter):
	def __init__(self, field_info:FieldInfo):
		super().__init__(field_info)

		field_type = self.field_info.field_type
		field_primary_key_name = field_info.field_type.FieldsInfo.primary_key_name

		# Create foreign key column:
		self.fk_name = f"{self.field_info.field_name}_fk"
		self.fk_type = field_type.FieldsInfo.get_field_type(field_primary_key_name)
		fk_column = Column(self.fk_name, type_map[self.fk_type], ForeignKey(f"{type_table_name(field_type)}.{field_primary_key_name}"))

		self.columns = [fk_column]

		self.relationships = {
			self.field_info.field_name : relationship(field_type, uselist=False)
		}

class OneToMany_List(GetterSetter):
	def __init__(self, field_info:FieldInfo, mapper_registry:registry):
		super().__init__(field_info)
		
		# Create intermediary table:
		self.mapping_table_name = f"{field_info.parent_type.__name__}_{field_info.field_name}_mapping"


		self.fk_name_parent = f"{field_info.parent_type.__name__}_fk"
		self.fk2_name_field = f"{field_info.field_type.__name__}_fk"

		parent_primary_key_name = field_info.parent_type.FieldsInfo.primary_key_name
		field_primary_key_name = field_info.field_type.FieldsInfo.primary_key_name
		self.mapping_table = Table(
			self.mapping_table_name,
			mapper_registry.metadata,
			Column(
				self.fk_name_parent,
				field_info.parent_type.FieldsInfo.get_field_type(parent_primary_key_name),
				ForeignKey(f"{type_table_name(field_info.parent_type)}.{parent_primary_key_name}")
			),
			Column(
				self.fk2_name_field,
				field_info.field_type.FieldsInfo.get_field_type(field_primary_key_name),
				ForeignKey(f"{type_table_name(field_info.field_type)}.{field_primary_key_name}")
			)
		)

		self.relationships = {
			self.field_info.field_name : relationship(field_info.field_type, secondary=self.mapping_table)
		}

def to_sql():
	'''
	Creates an SQLAlchemy schema class equivalent of the decorated class.
	
	Adds the schema class as a child class to the decorated class.
	
	That internal schema class will also hold a back reference to the decorated
	class to facilitate two-way type conversion.
	
	Then it adds a to_schema method to the decorated class, and a to_model method
	to the internal schema class to enable type conversion.
	
	By convention dataclass field metadata will contain any number of keys to guide
	the creation of the column for a given field on cls:
	1. "Column" = Column(...) will let the user directly specify the column to use in the schema class
	2. "primary_key" = True will make the column the primary key
	3. "type" = <sqlalchemy.Type> will specify the type of the column, eg Column(Integer), Column(String), etc
	4. "to_schema" = <Callable> will specify a function to convert the field to a schema equivalent
	5. "from_schema" = <Callable> will specify a function to convert the field from a schema equivalent
	
	Any thing that is not a default sqlalchemy type without a "Column" key, "type" key, or "to_schema"
	and "from_schema" keys, but that has a "__SQL_Schema_Class__" will create a relationship to the
	__SQL_Schema_Class__.__tablename__ table with the same name as the field.
	
	If it is a list, tuple, or set, an intermediary table will be created to hold the relationship.
	
	:param cls: The class to add the to_schema method to and to create the schema class from.
	:param Base: The SQLAlchemy Base class to inherit the schema class from.
	:param excluded_fields: A list of fields on cls to exclude from the schema class.
	:param included_fields: A list of fields on cls to include in the schema class.
	:param auto_include_fields: Whether or not to automatically include all fields on cls in the schema class.
	:param exclude_prefix: A prefix to exclude fields from the schema class.
	:return: The decorated class.
	'''
	def decorator(cls:Type[Any], mapper_registry:registry):
		getter_setters = []

		create_column = True
		def add_column(field_info:FieldInfo,column:Column):
			nonlocal create_column
			getter_setters.append(SimpleOneToOne(field_info, column))
			create_column = False
			
		for fi in cls.FieldsInfo.iterate_cls(0):
			field_name = fi.field_name
			field_type = fi.field_type
			create_column = True
			
			if field_name in fi.parent_type.FieldsInfo.fields_dict:
				field = fi.parent_type.FieldsInfo.fields_dict[field_name]
				if "Column" in field.metadata:
					add_column(fi, field.metadata["Column"])
				elif "type" in field.metadata:
					add_column(fi, Column(field_name, fi.metadata["type"], primary_key=fi.is_primary_key))

			if create_column:
				if fi.is_dataclass:
					getter_setters.append(OneToOneReference(fi))
				elif field_type is list:
					getter_setters.append(OneToMany_List(fi))
				else:
					add_column(fi, Column(field_name, type_map[field_type], primary_key=fi.is_primary_key))

		columns = []
		relationships = {}
		for gs in getter_setters:
			columns.extend(gs.columns)
			for relationship_name, relationship in gs.relationships.items():
				relationships[relationship_name] = relationship
				
		cls_table = Table(type_table_name(cls), mapper_registry.metadata, *columns)
		mapper_registry.map_imperatively(cls, cls_table, properties=relationships)
		return cls
	return decorator

