from sqlalchemy import Column, String, Integer,  ForeignKey, DateTime, JSON, Enum, Boolean, Float, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from typing import Type, Iterable, Tuple, Dict, Any, Union, Callable, List, Set
from itertools import chain
from datetime import datetime
from sqlalchemy.ext.declarative import declared_attr

from dataclasses import field, is_dataclass, dataclass, fields

type_map = {
	bool: Boolean,
    int: Integer,
	float: Float,
    str: Text,
	
    datetime: DateTime
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
		inclusion_set, 
		(
			attr for attr in dir(cls) if 
			not callable(getattr(cls, attr)) 
			and not safe_starts_with(attr, exclude_prefix)
		) if auto_include_fields else []
	) if attr not in exclusion_set))
	
	#Order field_names in the order they were defined in cls
	field_names = sorted(field_names, key=lambda x: list(cls.__annotations__).index(x) if x in cls.__annotations__ else float('inf'))
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
	primary_key_field_name = "__primary_key_name__"
	inner_schema_class_name = "__SQL_Schema_Class__"
	
	excluded_fields = chain(excluded_fields, [
		primary_key_field_name,
		inner_schema_class_name
	])
	
	field_names, fields_dict = get_fields_to_save(cls, excluded_fields, included_fields, auto_include_fields, exclude_prefix)
	
	#Get the primary key name:
	primary_key_name = None
	if hasattr(cls, primary_key_field_name):
		primary_key_name = cls.__primary_key_name__
		
	for field_name in field_names:
		field = fields_dict[field_name]
		if "primary_key" in field.metadata and field.metadata["primary_key"]:
			if primary_key_name is not None:
				raise ValueError(f"Multiple primary keys specified in {cls}.")
			primary_key_name = field_name

	if primary_key_name is None:
		if 'id' in field_names:
			primary_key_name = 'id'
		else:
			raise ValueError(f"No primary key specified for {cls}.")
	
	#Create the schema class:
	new_schema_class_name = f"{cls.__name__}_schema"
	class DynamicBase:
		__tablename__ = f"{cls.__name__}_Table"
		__model_class__ = cls
		__field_names__ = field_names
		__relationship_info__ = {}
		__primary_key_name__ = primary_key_name
		
		def to_model(self) -> cls:
			'''Converts the internal schema class to the decorated dataclass.'''
			model = self.__model_class__()
			for field_name in self.__field_names__:
				setattr(model, field_name, getattr(self, field_name))
			return model
	
	def to_schema(self) -> DynamicBase:
		'''Converts the decorated dataclass to the internal schema class.'''
		schema_class:DynamicBase = getattr(self, inner_schema_class_name)
		
		schema = schema_class()
		for field_name in schema_class.__field_names__:
			setattr(schema, field_name, getattr(self, field_name))
			
		for field_name, relationship_info in schema_class.__relationship_info__.items():
			setattr(schema, relationship_info["foreign_name"], getattr(self, relationship_info["primary_key_name"]))
		return schema
	
	# Create the columns for the schema class:
	def auto_create_field(field_name:str, field_type:Type[Any]):
		if field_type in type_map:
			setattr(DynamicBase, field_name, Column(type_map[field_type], primary_key=field_name==primary_key_name))
		#TODO: elif field_type is a list, tuple, or set, assert that it is a iterable of a
		#class with a __SQL_Schema_Class__, and create a relationship to that class with an
		#intermediary table to hold the relationship.
		
		elif inner_schema_class_name in field_type.__dict__:
			fields_schema_class = getattr(field_type, inner_schema_class_name)
			
			foreign_name = f"{field_name}__{fields_schema_class.__primary_key_name__}"
			fields_primary_key_column:Column = getattr(fields_schema_class, fields_schema_class.__primary_key_name__)
			fields_primary_key_type = fields_primary_key_column.type
			
			setattr(DynamicBase, foreign_name, Column(fields_primary_key_type))
			
			@declared_attr
			def get_relationship(cls):
				return relationship(
					fields_schema_class.__name__,
					primaryjoin=f"and_({fields_schema_class.__name__}.{fields_schema_class.__primary_key_name__}==foreign({new_schema_class_name}.{foreign_name}))",
					viewonly=True,
				)
			DynamicBase.__relationship_info__[field_name] = {"foreign_name": foreign_name, "primary_key_name": fields_schema_class.__primary_key_name__}
			setattr(DynamicBase, field_name, get_relationship)
		else:
			raise ValueError(f"Unsupported type {field_type} for field {field_name}")
	
	for field_name in field_names:
		if field_name in fields_dict:
			field = fields_dict[field_name]
			if "Column" in field.metadata:
				setattr(DynamicBase, field_name, field.metadata["Column"])
			elif "type" in field.metadata:
				setattr(DynamicBase, field_name, Column(field.metadata["type"], primary_key=field_name==primary_key_name))
			else:
				auto_create_field(field_name, field.type)
		else:
			auto_create_field(field_name, field.type)
	#remove all relationship info keys from field names:
	for field_name in DynamicBase.__relationship_info__.keys():
		DynamicBase.__field_names__.remove(field_name)
	
	setattr(cls, inner_schema_class_name, type(new_schema_class_name, (DynamicBase, Base), {}))
	setattr(cls, 'to_schema', to_schema)
	return cls

if __name__ == "__main__":
	from dataclasses import dataclass
	from sqlalchemy import create_engine
	from sqlalchemy.orm import sessionmaker
	
	engine = create_engine('sqlite:///:memory:', echo=True)
	Session = sessionmaker(bind=engine)
	
	# class TestClass_schema(DefaultBase):
	# 	__tablename__ = 'testclass'
	# 	__primary_key_name__ = 'Field1'

	# 	Field1 = Column(String, primary_key=True)
	# 	Field2 = Column(Integer)
	# 	Field3 = Column(Float)
	# 	Field4 = Column(Boolean)
	# 	Field5 = Column(DateTime, default=datetime.now)
	
	# class bla:
	# 	class TestClass2_schema(DefaultBase):
	# 		__tablename__ = 'testclass2'
	# 		__primary_key_name__ = 'Field2'

	# 		Field1 = Column(String)
	# 		Field2 = Column(Integer, primary_key=True)

	# 		# Auto-created relationship fields
	# 		Field3__Field1 = Column(String)
	# 		Field3 = relationship(
	# 			'TestClass_schema',
	# 			primaryjoin="and_(TestClass_schema.Field1==foreign(TestClass2_schema.Field3__Field1))",
	# 			viewonly=True
	# 		)
		
	
		
	@to_sql
	@dataclass
	class TestClass:
		__primary_key_name__ = "field1"
		field1: str = "test"
		field2: int	= 1
		field3: float = 1.0
		field4: bool = True
		field5: datetime = field(default_factory=datetime.now)
	
	@to_sql
	@dataclass
	class TestClass2:
		__primary_key_name__ = "field2"
		field1: str = "test"
		field2: int	= 1
		field3: TestClass = field(default_factory=TestClass)
	
	
		
	test = TestClass()
	test1 = TestClass()
	test1.field2 = 55
	test2 = TestClass2()
	test2.field3 = test
	
	DefaultBase.metadata.create_all(engine)
	
	# session = Session()
	# # Create instances of TestClass_schema and TestClass2_schema
	# test1 = TestClass_schema(Field1="test1", Field2=1, Field3=1.0, Field4=True)
	# test2 = bla.TestClass2_schema(Field1="test2", Field2=2, Field3__Field1="test1")

	# # Add instances to session
	# session.add(test1)
	# session.add(test2)
	
	
	# session.commit()
	
	# obj = session.query(TestClass_schema).all()
	# obj2 = session.query(bla.TestClass2_schema).all()
	
	session = Session()
	s = test.to_schema()
	
	s2 = test2.to_schema()
	session.add(s)
	session.add(s2)
	
	session.commit()
	
	obj = session.query(TestClass.__SQL_Schema_Class__).all()
	obj2 = session.query(TestClass2.__SQL_Schema_Class__).all()
	
	
	print()