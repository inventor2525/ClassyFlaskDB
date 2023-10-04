import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dataclasses import dataclass, field
from datetime import datetime

from Attributes.to_sql import to_sql, DefaultBase # Your specific import

class TestSQLAlchemyDataClasses(unittest.TestCase):
	def __create_db__(self):
		self.engine = create_engine('sqlite:///:memory:', echo=True)
		Session = sessionmaker(bind=self.engine)
		DefaultBase.metadata.create_all(self.engine)
		self.session = Session()
	def test_fields_are_equal(self):
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
		
		
		# Arrange
		test1 = TestClass()
		test2 = TestClass2()
		test2.field3 = test1
		
		self.session.add(test1.to_schema())
		self.session.add(test2.to_schema())
		self.session.commit()
		
		# Act
		obj = self.session.query(TestClass.__SQL_Schema_Class__).first()
		obj2 = self.session.query(TestClass2.__SQL_Schema_Class__).first()
		
		# Assert
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
		
if __name__ == '__main__':
	unittest.main()
