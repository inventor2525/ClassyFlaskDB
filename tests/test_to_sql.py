import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dataclasses import dataclass, field
from datetime import datetime

from ClassyFlaskDB.to_sql import to_sql, DefaultBase # Your specific import

from typing import List

class TestSQLAlchemyDataClasses(unittest.TestCase):
	def __create_db__(self):
		self.engine = create_engine('sqlite:///:memory:', echo=True)
		Session = sessionmaker(bind=self.engine)
		DefaultBase.metadata.create_all(self.engine)
		self.session = Session()
		
	def test_fields_are_equal(self):
		# Create test database
		@to_sql
		@dataclass
		class TestClass:
			__primary_key_name__ = "field1"
			field1: str = "test"
			field2: int = 1
			field3: float = 1.0
			field4: bool = True
			field5: datetime = field(default_factory=datetime.now)
		
		@to_sql
		@dataclass
		class TestClass2:
			__primary_key_name__ = "field2"
			field1: str = "test"
			field2: int = 1
			field3: TestClass = field(default_factory=TestClass)
		
		self.__create_db__()
		
		# Create test data
		test1 = TestClass()
		test2 = TestClass2()
		test2.field3 = test1
		
		# Add test data to database
		self.session.add(test1.to_schema())
		self.session.add(test2.to_schema())
		self.session.commit()
		
		# Query test data from database
		obj = self.session.query(TestClass.__SQL_Schema_Class__).first()
		obj2 = self.session.query(TestClass2.__SQL_Schema_Class__).first()
		
		# Assert test data is equal
		self.assertEqual(obj.field1, "test")
		self.assertEqual(obj.field2, 1)
		self.assertEqual(obj.field3, 1.0)
		self.assertEqual(obj.field4, True)
		
		self.assertEqual(obj2.field1, "test")
		self.assertEqual(obj2.field2, 1)
		self.assertEqual(obj2.field3.field1, obj.field1)
		self.assertEqual(obj2.field3.field2, obj.field2)
		self.assertEqual(obj2.field3.field3, obj.field3)
		self.assertEqual(obj2.field3.field4, obj.field4)
	
	def test_lists(self):
		# Create test database
		@to_sql
		@dataclass
		class TestClass:
			__primary_key_name__ = "field1"
			field1: int = 1
			field2: str = "test"
		
		@to_sql
		@dataclass
		class TestClass2:
			__primary_key_name__ = "field1"
			field1: int = 1
			list1: List[TestClass] = field(default_factory=list)
		
		self.__create_db__()
		
		# Create test data
		test1 = TestClass(field1=1, field2="a thing")
		test2 = TestClass(field1=2, field2="another thing")
		test3 = TestClass(field1=3, field2="a third thing")
		test_list = TestClass2()
		test_list.list1.append(test1)
		test_list.list1.append(test2)
		test_list.list1.append(test3)
		
		# Add test data to database
		self.session.add(test1.to_schema())
		self.session.add(test2.to_schema())
		self.session.add(test3.to_schema())
		self.session.add(test_list.to_schema())
		self.session.commit()
		
		# Query test data from database
		obj = self.session.query(TestClass.__SQL_Schema_Class__).all()
		obj2 = self.session.query(TestClass2.__SQL_Schema_Class__).first()
		
		# Assert test data is equal
		# Check test 1, 2, and 3
		self.assertEqual(obj[0].field1, 1)
		self.assertEqual(obj[0].field2, "a thing")
		
		self.assertEqual(obj[1].field1, 2)
		self.assertEqual(obj[1].field2, "another thing")
		
		self.assertEqual(obj[2].field1, 3)
		self.assertEqual(obj[2].field2, "a third thing")
		
		# Check test list
		self.assertEqual(obj2.field1, 1)
		self.assertEqual(len(obj2.list1), 3)
		
		self.assertEqual(obj2.list1[0].field1, obj[0].field1)
		self.assertEqual(obj2.list1[0].field2, obj[0].field2)
		
		self.assertEqual(obj2.list1[1].field1, obj[1].field1)
		self.assertEqual(obj2.list1[1].field2, obj[1].field2)
		
		self.assertEqual(obj2.list1[2].field1, obj[2].field1)
		self.assertEqual(obj2.list1[2].field2, obj[2].field2)
		
		
		
if __name__ == '__main__':
	unittest.main()
