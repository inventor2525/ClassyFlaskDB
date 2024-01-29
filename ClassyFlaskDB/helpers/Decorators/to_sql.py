from sqlalchemy import Table, Column, String, Integer, ForeignKey, DateTime, JSON, Enum, Boolean, Float, Text
from sqlalchemy.orm import declarative_base, relationship, registry
from sqlalchemy.ext.declarative import declared_attr, DeclarativeMeta
from datetime import datetime
from ClassyFlaskDB.helpers.Decorators.capture_field_info import FieldInfo
from sqlalchemy.sql import expression
from sqlalchemy import text

from ClassyFlaskDB.helpers import *
from dateutil import tz
import pytz

from dataclasses import fields, is_dataclass, MISSING
from sqlalchemy import event

type_map = {
	bool: Boolean,
	int: Integer,
	float: Float,
	str: Text,
	dict: JSON,
	
	# datetime: DateTime,
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
	def __init__(self, field_info: FieldInfo):
		super().__init__(field_info)

		field_type = self.field_info.field_type
		field_primary_key_name = field_info.field_type.FieldsInfo.primary_key_name

		# Create foreign key column:
		self.fk_name = f"{self.field_info.field_name}_fk"
		self.fk_type = field_type.FieldsInfo.get_field_type(field_primary_key_name)
		fk_column = Column(self.fk_name, type_map[self.fk_type], ForeignKey(f"{type_table_name(field_type)}.{field_primary_key_name}"))

		self.columns = [fk_column]

		self.relationships = {
			self.field_info.field_name: relationship(
				field_type,
				uselist=False,
				foreign_keys=[fk_column],
				post_update=True,
				primaryjoin=lambda: fk_column == getattr(field_type, field_primary_key_name),
				remote_side=lambda: getattr(field_type, field_primary_key_name)
			)
		}
class OneToMany_List(GetterSetter):
	def __init__(self, field_info:FieldInfo, mapper_registry:registry):
		super().__init__(field_info)
		
		# Create intermediary table:
		self.mapping_table_name = f"{field_info.parent_type.__name__}_{field_info.field_name}_mapping"

		self.fk_name_parent = f"{field_info.parent_type.__name__}_fk"
		self.fk_name_field = f"{field_info.field_name}_fk"

		parent_primary_key_name = field_info.parent_type.FieldsInfo.primary_key_name
		#Get the type inside any collection like foo from list[foo] or foo from tuple[foo] or foo from set[foo], and get its primary key name from its FieldsInfo where field_info.field_type is something like list[foo] or tuple[foo] or set[foo]:
		field_type = field_info.field_type.__args__[0]
		field_primary_key_name = field_type.FieldsInfo.primary_key_name
		self.mapping_table = Table(
			self.mapping_table_name,
			mapper_registry.metadata,
			Column(
				self.fk_name_parent,
				type_map[field_info.parent_type.FieldsInfo.get_field_type(parent_primary_key_name)],
				ForeignKey(f"{type_table_name(field_info.parent_type)}.{parent_primary_key_name}")
			),
			Column(
				self.fk_name_field,
				type_map[field_type.FieldsInfo.get_field_type(field_primary_key_name)],
				ForeignKey(f"{type_table_name(field_type)}.{field_primary_key_name}")
			)
		)

		self.relationships = {
			self.field_info.field_name: relationship(
				field_type,
				secondary=self.mapping_table
				# primaryjoin=self.fk_name_parent == self.mapping_table.c[self.fk_name_parent],
				# secondaryjoin=self.fk_name_field == self.mapping_table.c[self.fk_name_field]
			)
		}
def add_dynamic_datetime_property(cls, field_name):
	"""Adds dynamic properties to handle datetime with timezone."""
	def getter(self):
		datetime_val = getattr(self, f"{field_name}__DateTimeObj")
		timezone_str = getattr(self, f"{field_name}__TimeZone")
		if datetime_val and timezone_str:
			return datetime_val.replace(tzinfo=pytz.timezone(timezone_str))
		return datetime_val

	def setter(self, value):
		if value:
			setattr(self, f"{field_name}__DateTimeObj", value.replace(tzinfo=None))
			if value.tzinfo:
				# Store IANA timezone identifier if available
				timezone = getattr(value.tzinfo, 'zone', None)
				if timezone is None and hasattr(value.tzinfo, 'tzname'):
					timezone = value.tzinfo.tzname(value)
				setattr(self, f"{field_name}__TimeZone", timezone)
			else:
				setattr(self, f"{field_name}__TimeZone", None)
		else:
			setattr(self, f"{field_name}__DateTimeObj", None)
			setattr(self, f"{field_name}__TimeZone", None)

	setattr(cls, f"{field_name}__DateTimeObj", None)
	setattr(cls, f"{field_name}__TimeZone", None)
	setattr(cls, field_name, property(getter, setter))
	
class DateTimeGetterSetter(GetterSetter):
	def __init__(self, field_info:FieldInfo):
		super().__init__(field_info)

		self.datetime_column = Column(f"{self.field_info.field_name}__DateTimeObj", DateTime)
		self.timezone_column = Column(f"{self.field_info.field_name}__TimeZone", String, nullable=True)
		self.columns = [self.datetime_column, self.timezone_column]
		
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
	
	
	#Add this somewhere      https://chat.openai.com/c/ba9203f1-adc5-44e1-9099-df8c4cbba7c5
	
	
	
	
	def decorator(cls:Type[Any], mapper_registry:registry):
		getter_setters = []

		cls_parent_type = cls.__bases__[0]
		cls_is_base = cls_parent_type is object
		cls_has_children = len(cls.__subclasses__()) > 0

		create_column = True
		def add_column(field_info:FieldInfo,column:Column):
			nonlocal create_column
			getter_setters.append(SimpleOneToOne(field_info, column))
			create_column = False
		def create_col(field_info:FieldInfo, col_type:type):
			if not cls_is_base and field_info.is_primary_key:
				parent_primary_key_name = cls_parent_type.FieldsInfo.primary_key_name
				add_column(field_info, Column(field_info.field_name, col_type, ForeignKey(f"{type_table_name(cls_parent_type)}.{parent_primary_key_name}"), primary_key=field_info.is_primary_key))
			else:
				add_column(field_info, Column(field_info.field_name, col_type, primary_key=field_info.is_primary_key))

		for fi in cls.FieldsInfo.iterate(0):
			field_name = fi.field_name
			field_type = fi.field_type
			create_column = True
			
			if not cls_is_base:
				if field_name in cls_parent_type.__dict__:
					if not fi.is_primary_key:
						continue
			
			if field_name in fi.parent_type.FieldsInfo.fields_dict:
				field = fi.parent_type.FieldsInfo.fields_dict[field_name]
				if "Column" in field.metadata:
					add_column(fi, field.metadata["Column"])
				elif "type" in field.metadata:
					create_col(fi, field.metadata["type"])

			if create_column:
				if fi.is_dataclass:
					getter_setters.append(OneToOneReference(fi))
				#figure out if field_type which might be like this "list[__main__.Bar]" is a list:
				elif hasattr(field_type, "__origin__") and field_type.__origin__ in [list, tuple, set]:
					getter_setters.append(OneToMany_List(fi, mapper_registry))
				elif field_type is datetime:
					getter_setters.append(DateTimeGetterSetter(fi))
					add_dynamic_datetime_property(cls, fi.field_name)
				else:
					origin_type = get_origin(field_type)
					if origin_type:
						field_type = origin_type
					mapped_type = type_map.get(field_type, None)
					if mapped_type:
						create_col(fi, mapped_type)

		columns = []
		relationships = {}
		for gs in getter_setters:
			columns.extend(gs.columns)
			for relationship_name, relationship in gs.relationships.items():
				# print(f"Setting up relationship for {cls.__name__}: {relationship_name} -> {relationship}")
				relationships[relationship_name] = relationship
		
		if cls_is_base:
			if cls_has_children:
				polymorphic_descriminator = Column('__cls_type__', String)
				columns.append(polymorphic_descriminator)
				cls_table = Table(type_table_name(cls), mapper_registry.metadata, *columns)
				mapper_registry.map_imperatively(cls, cls_table, properties=relationships,
					polymorphic_identity=cls.__name__, polymorphic_on=polymorphic_descriminator
				)
			else:
				cls_table = Table(type_table_name(cls), mapper_registry.metadata, *columns)
				mapper_registry.map_imperatively(cls, cls_table, properties=relationships)
		else:
			cls_table = Table(type_table_name(cls), mapper_registry.metadata, *columns)
			parent_table = getattr(cls_parent_type, "__table__")
			mapper_registry.map_imperatively(cls, cls_table,
				inherits=cls_parent_type,
				polymorphic_identity=cls.__name__,
				inherit_condition=(getattr(cls_table.c, cls.FieldsInfo.primary_key_name) == getattr(parent_table.c, cls_parent_type.FieldsInfo.primary_key_name)),
				properties=relationships
			)
		
		def initialize_missing_dataclass_fields(target, context):
			for field in fields(target):
				# Check if the field is not already set
				if not hasattr(target, field.name):
					value = MISSING
					if field.default is not MISSING: # Handle default values
						value = field.default
					elif field.default_factory is not MISSING:  # Handle default factories
						value = field.default_factory()

					if value is not MISSING:
						setattr(target, field.name, value)
		event.listen(cls, 'load', initialize_missing_dataclass_fields)
		setattr(cls, "__table__", cls_table)
		return cls
	return decorator