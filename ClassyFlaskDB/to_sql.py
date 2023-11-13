from sqlalchemy import Table, Column, String, Integer, ForeignKey, DateTime, JSON, Enum, Boolean, Float, Text
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.declarative import declared_attr, DeclarativeMeta
from datetime import datetime

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

	def append_to_schema(self, schema):
		pass
	def set_on_model(self):
		pass
	def set_on_schema(self):
		pass

class SimpleOneToOne(GetterSetter):
	def __init__(self, field_info:FieldInfo, column:Column):
		super().__init__(field_info)
		self.column = column
		
	def append_to_schema(self, schema):
		# Add column to schema:
		setattr(schema, self.field_info.field_name, self.column)
	
	def set_on_model(self, model, schema):
		setattr(model, self.field_info.field_name, getattr(schema, self.field_info.field_name))
	def set_on_schema(self, model, schema):
		setattr(schema, self.field_info.field_name, getattr(model, self.field_info.field_name))

class OneToOneReference(GetterSetter):
	def __init__(self, field_info:FieldInfo):
		super().__init__(field_info)
		
	def append_to_schema(self, schema):
		field_type = self.field_info.field_type
		self.primary_key_name = field_type.FieldsInfo.__primary_key_name__

		# Create foreign key column:
		self.fk_name = f"{self.field_info.field_name}_fk"
		self.fk_type = field_type.get_field_type(self.primary_key_name)
		fk_column = Column(self.fk_name, type_map[self.fk_type], ForeignKey(f"{type_table_name(field_type)}.{self.primary_key_name}"))

		# Add foreign key column to schema:
		setattr(schema, self.fk_name, fk_column)

		# Add relationship to schema:
		r = relationship(
			type_table_name(field_type),
			primaryjoin=f"and_({type_table_name(field_type)}.{self.primary_key_name}==foreign({type_table_name(self.field_info.parent_class)}.{self.fk_name}))",
			viewonly=True,
			uselist=False
		)
		setattr(schema, self.field_info.field_name, r)

	def set_on_model(self, model, schema):
		setattr(model, self.field_info.field_name, getattr(schema, self.field_info.field_name))
	
	def set_on_schema(self, model, schema):
		setattr(schema, self.fk_name, getattr(model, self.primary_key_name))

class OneToMany_List(GetterSetter):
	def __init__(self, field_info:FieldInfo):
		super().__init__(field_info)

	def append_to_schema(self, schema):
		
		# Create intermediary table:
		self.mapping_table_name = f"{self.field_info.parent_class.__name__}_{self.field_info.field_name}_mapping"
		self.mapping_table = Table(
			self.mapping_table_name,
			Base.metadata,
			Column(self.fk1_name, ForeignKey(f"{type_table_name(self.field_info.parent_class)}.{self.primary_key_name}")),
			Column(self.fk2_name, ForeignKey(f"{type_table_name(self.field_info.field_type)}.{self.primary_key_name}"))
		)

		# Add intermediary table to schema:
		setattr(schema, self.mapping_table_name, self.mapping_table)

		# Add relationship to schema:
		r = relationship(
			type_table_name(self.field_info.field_type),
			secondary=self.mapping_table,
			backref=f"{self.field_info.parent_class.__name__}_mapping"
		)
		setattr(schema, self.field_info.field_name, r)

	def set_on_model(self, model, schema):
		pass

	def set_on_schema(self, model, schema):
		pass

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
	def decorator(cls:Type[Any], Base:DeclarativeMeta):
		table_name = f"{cls.__name__}_Table"
		getter_setters = []

		create_column = True
		def add_column(field_name:str, column:Column):
			nonlocal create_column
			getter_setters.append(SimpleOneToOne(field_name, column))
			create_column = False
			
		for fi in cls.FieldsInfo.iterate_cls(0):
			field_name = fi.field_name
			field_type = fi.field_type
			create_column = True
			
			if field_name in fi.fields_dict:
				field = fi.fields_dict[field_name]
				if "Column" in field.metadata:
					add_column(field.metadata["Column"])
				elif "type" in field.metadata:
					add_column(Column(fi.metadata["type"], primary_key=fi.is_primary_key))

			if create_column:
				if fi.is_dataclass:
					getter_setters.append(OneToOneReference(fi))
				elif field_type is list:
					getter_setters.append(OneToMany_List(fi))
				else:
					add_column(Column(type_map[field_type], primary_key=fi.is_primary_key))

		cls_table = Table(table_name, Base.metadata, *columns)
		setattr(cls, 'to_schema', to_schema)
		return cls
	return decorator

