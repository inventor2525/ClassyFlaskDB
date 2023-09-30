from sqlalchemy import Column, String, Integer,  ForeignKey, DateTime, JSON, Enum, Boolean, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from typing import Type, Iterable, Tuple, Dict, Any, Union, Callable, List, Set
from itertools import chain
from datetime import datetime

from dataclasses import fields, is_dataclass

type_map = {
	bool: Boolean,
    int: Integer,
	float: Float,
    str: Text,
	
    datetime: DateTime,
	
	list: JSON,
	tuple: JSON,
	set: JSON,
}

def get_fields_to_save(
		cls:Type[Any], 
		excluded_fields:Iterable[str]=[], included_fields:Iterable[str]=[],
		auto_include_fields=True, exclude_prefix:str="_"
	) -> Tuple[Set[str], Dict[str, field]]:
	
	inclusion_set = set(included_fields)
	exclusion_set = set(excluded_fields)
	
	fields_dict = {}
	if is_dataclass(cls):
		fields_dict = {f.name: f for f in fields(cls)}
		
		# Get any fields that have information about what we might
		# want to do with them in sql in in their metadata
		def handle_should_save(field):
			'''
			Adds the field to the exclusion or inclusion set based on if metadata
			contains should_save and returns whether or not it did contain should_save.
			'''
			if "should_save" in field.metadata:
				if not field.metadata["should_save"]:
					exclusion_set.add(field.name)
				else:
					inclusion_set.add(field.name)
				return True
			return False
			
		for field in fields_dict.values():
			if "internal" in field.metadata:
				if not handle_should_save(field):
					exclusion_set.add(field.name)
			else:
				if not handle_should_save(field):
					if auto_include_fields:
						inclusion_set.add(field.name)	
								
	def safe_starts_with(s:str, prefix:str):
		if prefix is None or len(prefix)==0:
			return False
		return s.startswith(prefix)
		
	field_names = set((attr for attr in chain(
		included_fields, 
		(
			attr for attr in dir(cls) if 
			not callable(getattr(cls, attr)) 
			and not safe_starts_with(attr, exclude_prefix)
		) if auto_include_fields else []
	) if attr not in excluded_fields))
	
	#TODO: order field_names in the order they were defined in cls
	return field_names, fields_dict

DefaultBase = declarative_base()
def to_sql(cls:Type[Any], Base=DefaultBase, excluded_fields:Iterable[str]=[], included_fields:Iterable[str]=[], auto_include_fields=True, exclude_prefix:str="_"):
	'''
	Creates an SQLAlchemy schema class equivalent of the decorated class.
	
	Adds the schema class as a child class to the decorated class.
	
	That internal schema class will also hold a back reference to the decorated
	class to facilitate two-way type conversion.
	
	Then it adds a to_schema method to the decorated class, and a to_model method
	to the internal schema class to enable type conversion.
	'''
	field_names, fields_dict = get_fields_to_save(cls, excluded_fields, included_fields, auto_include_fields, exclude_prefix)
	
	inner_schema_class_name = "__SQL_Schema_Class__"
	
	primary_key_name = None
	#TODO: Asserting that there is exactly 1 primary key
	# find the name of the primary key in one of a number of places:
	# 1. A str field in cls named __primary_key__ that contains the name of the primary key
	# 2. The field with the metadata "primary_key"=True
	# 3. The field in cls named "id"
	
	class SQLSchema(Base):
		__tablename__ = f"{cls.__name__}_Table"
		__model_class__ = cls
		__field_names__ = field_names
		__primary_key_name__ = primary_key_name
		
		def to_model(self) -> cls:
			model = self.__model_class__()
			for field_name in self.__field_names__:
				setattr(model, field_name, getattr(self, field_name))
			return model
	
	def to_schema(self) -> SQLSchema:
		schema_class:SQLSchema = getattr(self, inner_schema_class_name)
		
		schema = schema_class()
		for field_name in schema_class.__field_names__:
			setattr(schema, field_name, getattr(self, field_name))
		return schema
		
	def auto_create_field(field_name:str, field_type:Type[Any]):
		if field_type in type_map:
			return Column(type_map[field_type])
		elif inner_schema_class_name in field_type.__dict__:
			fields_schema_class = getattr(field_type, inner_schema_class_name)
			
			#TODO: create a relationship to field types table with the same name as field_name
			#similar to this:
			# parent = relationship(
			# 		"Parent",
			# 		primaryjoin="and_(Parent.name==foreign(Child.parent_name))",
			# 		viewonly=True
			# )
			#
			# WIP code:
			# setattr(fields_schema_class, field_name, relationship(
			# 	field_type.__tablename__,
		else:
			raise ValueError(f"Unsupported type {field_type} for field {field_name}")
	
	# field metadata will contain any number of keys to guide the creation of the column for field_name:
	# 1. "Column" = Column(...) will let the user directly specify the column
	# 2. "primary_key" = True will make the column the primary key
	# 3. "type" = <sqlalchemy.Type> will specify the type of the column, eg Column(Integer), Column(String), etc
	# 4. "to_schema" = <Callable> will specify a function to convert the field to a schema equivalent
	# 5. "from_schema" = <Callable> will specify a function to convert the field from a schema equivalent
	
	for field_name in fields:
		if field_name in fields_dict:
			field = fields_dict[field_name]
			if "Column" in field.metadata:
				setattr(SQLSchema, field_name, field.metadata["Column"])
			elif "type" in field.metadata:
					Column(field.metadata["type"])
			else:
				setattr(SQLSchema, field_name, auto_create_field(field_name, field.type))
		else:
			setattr(SQLSchema, field_name, auto_create_field(field_name, field.type))
			
	setattr(cls, inner_schema_class_name, SQLSchema)
	setattr(cls, 'to_schema', to_schema)
	return cls