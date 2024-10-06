from zoneinfo import ZoneInfo
from ClassyFlaskDB.new.SQLStorageEngine import *
from ClassyFlaskDB.DefaultModel import get_local_time
import unittest
from enum import Enum
import time
import threading
import os

class newDATADecorator_tests(unittest.TestCase):
	def test_relationship(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		@dataclass
		class Foe:
			name: str
			strength: int

		@DATA
		@dataclass
		class Bar:
			name: str
			location: str
			foe: Foe = None
			
		data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)
		
		foe = Foe(name="Dragon", strength=100)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe)

		data_engine.merge(bar)
		
		# Query from database
		queried_bar = data_engine.query(Bar).filter_by_id(bar.get_primary_key())

		# Validate
		self.assertEqual(queried_bar.name, bar.name)
		self.assertEqual(queried_bar.location, bar.location)
		self.assertEqual(queried_bar.foe.name, foe.name)
		self.assertEqual(queried_bar.foe.strength, foe.strength)
	
	def test_set_before_read(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class ComplexObject:
			string_field: str = "default_string"
			int_field: int = 0
			dict_field: Dict[str, int] = field(default_factory=dict)
			list_field: List[str] = field(default_factory=list)

		engine = SQLStorageEngine("sqlite:///:memory:", DATA)

		# Create and store initial object
		initial_obj = ComplexObject(
			string_field="initial_string",
			int_field=42,
			dict_field={"key1": 1, "key2": 2},
			list_field=["item1", "item2"]
		)
		engine.merge(initial_obj)

		# Query the object from the database
		queried_obj = engine.query(ComplexObject).filter_by_id(initial_obj.get_primary_key())
		
		# Add these 2 lines and this test passes:
		#TODO: Why do I have to pre-read these for them to not get set to initial immediately 
        #after setting them, some sort of weird race condition, probably from it still
        #loading from the db, for some reason, after having complete the set operation?
		
		# queried_obj.string_field
		# queried_obj.int_field
		
		# Set values without accessing them first
		queried_obj.string_field = "new_string"
		queried_obj.int_field = 100

		# Assert that the new values are set correctly
		self.assertEqual(queried_obj.string_field, "new_string")
		self.assertEqual(queried_obj.int_field, 100)

		# Check that unmodified fields retain their original values
		self.assertEqual(queried_obj.dict_field, {"key1": 1, "key2": 2})
		self.assertEqual(queried_obj.list_field, ["item1", "item2"])

		# Modify fields after accessing them
		original_dict = queried_obj.dict_field
		self.assertEqual(original_dict, {"key1": 1, "key2": 2})
		queried_obj.dict_field = {"new_key": 3}
		self.assertEqual(queried_obj.dict_field, {"new_key": 3})

		original_list = queried_obj.list_field
		self.assertEqual(original_list, ["item1", "item2"])
		queried_obj.list_field = ["new_item"]
		self.assertEqual(queried_obj.list_field, ["new_item"])

		# Threaded modifications
		def modify_in_thread():
			time.sleep(0.1)  # Small delay to ensure the main thread has started
			queried_obj.string_field = "thread_string"
			queried_obj.int_field = 200

		thread = threading.Thread(target=modify_in_thread)
		thread.start()

		# Modify in main thread
		queried_obj.dict_field = {"main_key": 4}
		queried_obj.list_field = ["main_item"]

		thread.join()

		# Assert final state after threaded modifications
		self.assertEqual(queried_obj.string_field, "thread_string")
		self.assertEqual(queried_obj.int_field, 200)
		self.assertEqual(queried_obj.dict_field, {"main_key": 4})
		self.assertEqual(queried_obj.list_field, ["main_item"])

		# Requery to check persistence
		requeried_obj = engine.query(ComplexObject).filter_by_id(initial_obj.get_primary_key())
		self.assertEqual(requeried_obj.string_field, "thread_string")
		self.assertEqual(requeried_obj.int_field, 200)
		self.assertEqual(requeried_obj.dict_field, {"main_key": 4})
		self.assertEqual(requeried_obj.list_field, ["main_item"])
		
	def test_datetime_with_timezone(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class DateTimeObject:
			created_at: datetime

		data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

		# Create a datetime with timezone information
		original_dt = get_local_time()
		
		# Create and merge object
		dt_obj = DateTimeObject(created_at=original_dt)
		data_engine.merge(dt_obj)

		# Query and validate
		queried_obj = data_engine.query(DateTimeObject).filter_by_id(dt_obj.get_primary_key())

		# Check if the queried datetime has timezone information
		self.assertIsNotNone(queried_obj.created_at.tzinfo, "Deserialized datetime should have timezone information")

		# Check if the timezone matches the original
		self.assertEqual(queried_obj.created_at.tzinfo, original_dt.tzinfo, "Timezone information should match")

		# Check if the datetime values match (ignoring timezone)
		self.assertEqual(queried_obj.created_at.replace(tzinfo=None), 
						original_dt.replace(tzinfo=None), 
						"Datetime values should match when ignoring timezone")

		# Check if the complete datetime objects match (including timezone)
		self.assertEqual(queried_obj.created_at, original_dt, "Complete datetime objects should match")

		# Print for debugging
		print(f"Original datetime: {original_dt}")
		print(f"Queried datetime: {queried_obj.created_at}")
		
	def test_enum(self):
		class TestColor(Enum):
			RED = 1
			GREEN = 2
			BLUE = 3
		DATA = DATADecorator()

		@DATA
		@dataclass
		class ColorObject:
			name: str
			color: TestColor

		data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

		# Create and merge object
		color_obj = ColorObject("Sky", TestColor.BLUE)
		data_engine.merge(color_obj)

		# Query and validate
		queried_obj = data_engine.query(ColorObject).filter_by_id(color_obj.get_primary_key())
		self.assertEqual(queried_obj.name, "Sky")
		self.assertEqual(queried_obj.color, TestColor.BLUE)

		# Update and re-merge
		color_obj.color = TestColor.GREEN
		data_engine.merge(color_obj)

		# Query again and validate
		queried_obj = data_engine.query(ColorObject).filter_by_id(color_obj.get_primary_key())
		self.assertEqual(queried_obj.color, TestColor.GREEN)
		
	def test_relationship_with_circular_ref(self):
		def test_with_or_without_persisting(persist:bool):
			DATA = DATADecorator()

			# Define the data classes
			@DATA
			@dataclass
			class Foe:
				name: str
				strength: int
				bar: "Bar" = None

			@DATA
			@dataclass
			class Bar:
				name: str
				location: str
				foe: "Foe" = None
				
			data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

			foe = Foe(name="Dragon1", strength=100)
			bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe)

			foe.bar = bar

			# Insert into database
			data_engine.merge(bar, persist)

			# Query from database
			queried_bar = data_engine.query(Bar).filter_by_id(bar.get_primary_key())

			# Validate
			self.assertEqual(queried_bar.name, bar.name)
			self.assertEqual(queried_bar.location, bar.location)
			
			self.assertEqual(queried_bar.foe.name, bar.foe.name)
			self.assertEqual(queried_bar.foe.strength, bar.foe.strength)

			self.assertEqual(queried_bar.foe.bar.name, bar.name)
			self.assertEqual(queried_bar.foe.bar.location, bar.location)
			self.assertEqual(queried_bar.foe.bar.auto_id, bar.auto_id)
			
			if persist:
				self.assertEqual(id(bar), id(queried_bar))
				self.assertEqual(id(bar.foe), id(queried_bar.foe))
			else:
				self.assertNotEqual(id(bar), id(queried_bar))
				self.assertNotEqual(id(bar.foe), id(queried_bar.foe))
				
			self.assertEqual(id(queried_bar), id(queried_bar.foe.bar))
			self.assertEqual(id(queried_bar.foe), id(queried_bar.foe.bar.foe))
		test_with_or_without_persisting(True)
		test_with_or_without_persisting(False)
	
	def test_polymorphic_relationships(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		@dataclass
		class Foe:
			name: str
			strength: int
			
		@DATA
		@dataclass
		class SuperFoe(Foe):
			attack_multiplier : float

		@DATA
		@dataclass
		class Bar:
			name: str
			location: str
			foe: Foe = None
			
		data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)
		
		foe = SuperFoe(name="Dragon", strength=100, attack_multiplier=10)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe)

		data_engine.merge(bar)
		
		# Query from database
		queried_bar = data_engine.query(Bar).filter_by_id(bar.get_primary_key())

		# Validate
		self.assertEqual(queried_bar.name, bar.name)
		self.assertEqual(queried_bar.location, bar.location)
		self.assertEqual(type(queried_bar.foe), SuperFoe)
		self.assertEqual(queried_bar.foe.name, foe.name)
		self.assertEqual(queried_bar.foe.strength, foe.strength)
		self.assertEqual(queried_bar.foe.attack_multiplier, foe.attack_multiplier)
		
	def test_list_and_circular_ref(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class Person:
			name: str
			age: int
			height: float
			birth_date: datetime
			family: 'ImmediateFamily' = None

		@DATA
		@dataclass
		class ImmediateFamily:
			surname: str
			children: List[Person]
			parents: List[Person]

		data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

		# Create family members
		alice = Person("Alice", 10, 140.0, datetime(2013, 5, 15))
		bob = Person("Bob", 12, 150.0, datetime(2011, 3, 20))
		eve = Person("Eve", 35, 165.5, datetime(1988, 9, 22))
		adam = Person("Adam", 37, 180.0, datetime(1986, 3, 10))

		# Create family
		family = ImmediateFamily("Smith", [alice, bob], [eve, adam])

		# Set circular references
		alice.family = family
		bob.family = family
		eve.family = family
		adam.family = family

		# Merge into database
		data_engine.merge(alice)

		# Query from database
		queried_family = data_engine.query(Person).filter_by_id(eve.get_primary_key()).family

		# Validate family
		self.assertEqual(queried_family.surname, family.surname)
		self.assertEqual(len(queried_family.children), len(family.children))
		self.assertEqual(len(queried_family.parents), len(family.parents))

		# Validate children
		for original, queried in zip(family.children, queried_family.children):
			self.assertEqual(queried.name, original.name)
			self.assertEqual(queried.age, original.age)
			self.assertEqual(queried.height, original.height)
			self.assertEqual(queried.birth_date, original.birth_date)
			self.assertEqual(queried.family.surname, family.surname)
			self.assertIs(queried.family, queried_family)

		# Validate parents
		for original, queried in zip(family.parents, queried_family.parents):
			self.assertEqual(queried.name, original.name)
			self.assertEqual(queried.age, original.age)
			self.assertEqual(queried.height, original.height)
			self.assertEqual(queried.birth_date, original.birth_date)
			self.assertEqual(queried.family.surname, family.surname)
			self.assertIs(queried.family, queried_family)

		# Additional checks for circular references
		alice_queried, bob_queried = queried_family.children
		eve_queried, adam_queried = queried_family.parents

		# Check that children in parents' family are the same objects
		self.assertIs(eve_queried.family.children[0], alice_queried)
		self.assertIs(eve_queried.family.children[1], bob_queried)
		self.assertIs(adam_queried.family.children[0], alice_queried)
		self.assertIs(adam_queried.family.children[1], bob_queried)

		# Check that parents in children's family are the same objects
		self.assertIs(alice_queried.family.parents[0], eve_queried)
		self.assertIs(alice_queried.family.parents[1], adam_queried)
		self.assertIs(bob_queried.family.parents[0], eve_queried)
		self.assertIs(bob_queried.family.parents[1], adam_queried)
	
	def test_dictionary(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class DictContainer:
			name: str
			data: Dict[str, int]

		data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

		# Create and merge object
		dict_obj = DictContainer("Test Dict", {"a": 1, "b": 2, "c": 3})
		data_engine.merge(dict_obj)

		# Query and validate
		queried_obj = data_engine.query(DictContainer).filter_by_id(dict_obj.get_primary_key())
		self.assertEqual(queried_obj.name, "Test Dict")
		self.assertEqual(queried_obj.data, {"a": 1, "b": 2, "c": 3})

		# Update dictionary and re-merge
		dict_obj.data["d"] = 4
		dict_obj.data["b"] = 5
		data_engine.merge(dict_obj)

		# Query again and validate
		queried_obj = data_engine.query(DictContainer).filter_by_id(dict_obj.get_primary_key())
		self.assertEqual(queried_obj.data, {"a": 1, "b": 5, "c": 3, "d": 4})

		# Test lazy loading
		lazy_value = queried_obj.data["c"]
		self.assertEqual(lazy_value, 3)
	
	def test_simple_nested_lists(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class Bar:
			value: int

		@DATA
		@dataclass
		class Foo:
			name: str
			nested_bars: List[List[Bar]]

		data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

		# Create nested structure
		bar1 = Bar(1)
		bar2 = Bar(2)
		bar3 = Bar(3)
		bar4 = Bar(4)

		foo = Foo("TestFoo", [[bar1, bar2], [bar3, bar4]])

		# Merge into database
		data_engine.merge(foo)

		# Query from database
		queried_foo = data_engine.query(Foo).filter_by_id(foo.get_primary_key())

		# Validate
		self.assertEqual(queried_foo.name, "TestFoo")
		self.assertEqual(len(queried_foo.nested_bars), 2)
		self.assertEqual(len(queried_foo.nested_bars[0]), 2)
		self.assertEqual(len(queried_foo.nested_bars[1]), 2)

		# Check values
		self.assertEqual(queried_foo.nested_bars[0][0].value, 1)
		self.assertEqual(queried_foo.nested_bars[0][1].value, 2)
		self.assertEqual(queried_foo.nested_bars[1][0].value, 3)
		self.assertEqual(queried_foo.nested_bars[1][1].value, 4)

		# Modify and re-merge
		foo.nested_bars[0][1] = Bar(5)
		foo.nested_bars[1].append(Bar(6))

		data_engine.merge(foo)

		# Query again
		queried_foo = data_engine.query(Foo).filter_by_id(foo.get_primary_key())

		# Validate changes
		self.assertEqual(queried_foo.nested_bars[0][1].value, 5)
		self.assertEqual(len(queried_foo.nested_bars[1]), 3)
		self.assertEqual(queried_foo.nested_bars[1][2].value, 6)
		
	def test_nested_lists_and_circular_refs(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class Person:
			name: str
			age: int
			family: 'ImmediateFamily' = None

		@DATA
		@dataclass
		class ImmediateFamily:
			surname: str
			children: List[Person]
			parents: List[Person]
			grandparents: List[List[Person]]

		data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

		# Create family members
		alice = Person("Alice", 10)
		bob = Person("Bob", 12)
		eve = Person("Eve", 35)
		adam = Person("Adam", 37)
		
		# Grandparents
		gma_eve = Person("Grandma Eve", 60)
		gpa_eve = Person("Grandpa Eve", 62)
		gma_adam = Person("Grandma Adam", 61)
		gpa_adam = Person("Grandpa Adam", 63)

		# Create families
		smith_family = ImmediateFamily("Smith", [alice, bob], [eve, adam], [[gma_eve, gpa_eve], [gma_adam, gpa_adam]])
		eve_family = ImmediateFamily("Eve's Maiden", [eve], [gma_eve, gpa_eve], [])
		adam_family = ImmediateFamily("Adam's Maiden", [adam], [gma_adam, gpa_adam], [])

		# Set circular references
		alice.family = smith_family
		bob.family = smith_family
		eve.family = smith_family
		adam.family = smith_family
		gma_eve.family = eve_family
		gpa_eve.family = eve_family
		gma_adam.family = adam_family
		gpa_adam.family = adam_family

		# Merge into database
		data_engine.merge(alice)

		# Query from database
		queried_family = data_engine.query(ImmediateFamily).filter_by_id(smith_family.get_primary_key())

		# Validate
		self.assertEqual(queried_family.surname, "Smith")
		self.assertEqual(len(queried_family.children), 2)
		self.assertEqual(len(queried_family.parents), 2)
		self.assertEqual(len(queried_family.grandparents), 2)
		self.assertEqual(len(queried_family.grandparents[0]), 2)
		self.assertEqual(len(queried_family.grandparents[1]), 2)

		alice_queried = queried_family.children[0]
		bob_queried = queried_family.children[1]
		eve_queried = queried_family.parents[0]
		adam_queried = queried_family.parents[1]

		# Check grandparents
		gma_eve_queried = queried_family.grandparents[0][0]
		gpa_eve_queried = queried_family.grandparents[0][1]
		gma_adam_queried = queried_family.grandparents[1][0]
		gpa_adam_queried = queried_family.grandparents[1][1]

		# Validate grandparents
		self.assertEqual(gma_eve_queried.name, "Grandma Eve")
		self.assertEqual(gpa_eve_queried.name, "Grandpa Eve")
		self.assertEqual(gma_adam_queried.name, "Grandma Adam")
		self.assertEqual(gpa_adam_queried.name, "Grandpa Adam")

		# Check that grandparents list is the same object for all family members
		self.assertIs(queried_family.grandparents, alice_queried.family.grandparents)
		self.assertIs(queried_family.grandparents, bob_queried.family.grandparents)
		self.assertIs(queried_family.grandparents, eve_queried.family.grandparents)
		self.assertIs(queried_family.grandparents, adam_queried.family.grandparents)

		# Validate grandparents through immediate families
		self.assertEqual(eve_queried.family.parents[0].name, eve.name)
		self.assertEqual(eve_queried.family.parents[1].name, adam.name)
		self.assertEqual(adam_queried.family.parents[0].name, eve.name)
		self.assertEqual(adam_queried.family.parents[1].name, adam.name)

		# Check object identity
		self.assertIs(eve_queried.family.parents[0], eve_queried)
		self.assertIs(eve_queried.family.parents[1], adam_queried)
		self.assertIs(adam_queried.family.parents[0], eve_queried)
		self.assertIs(adam_queried.family.parents[1], adam_queried)
		
		self.assertEqual(gma_eve_queried.family.children[0].family.children[0].age, alice.age)
		self.assertEqual(gpa_adam_queried.family.children[0].family.children[1].age, bob.age)
		
	def test_hash_id(self):
		DATA = DATADecorator()

		class Color(Enum):
			RED = 1
			GREEN = 2
			BLUE = 3

		@DATA(id_type=ID_Type.HASHID)
		@dataclass
		class ComplexObject:
			name: str
			number: int
			date: datetime
			colors: List[Color]
			metadata: Dict[str, float]

		data_engine = SQLStorageEngine("sqlite:///:memory:", DATA)

		# Create initial object
		initial_obj = ComplexObject(
			name="Test Object",
			number=42,
			date=datetime(2023, 7, 21, 12, 0),
			colors=[Color.RED, Color.BLUE],
			metadata={"x": 1.5, "y": 2.7}
		)

		# Merge initial object
		data_engine.merge(initial_obj)

		# Query and confirm initial merge
		queried_obj = data_engine.query(ComplexObject).filter_by_id(initial_obj.get_primary_key())
		self.assertIsNotNone(queried_obj)
		self.assertEqual(queried_obj.name, "Test Object")
		self.assertEqual(queried_obj.number, 42)
		self.assertEqual(queried_obj.date, datetime(2023, 7, 21, 12, 0))
		# self.assertEqual(queried_obj.colors[0], Color.RED)
		# self.assertEqual(queried_obj.colors[1], Color.BLUE)
		self.assertEqual(queried_obj.colors, [Color.RED, Color.BLUE])
		self.assertEqual(queried_obj.metadata, {"x": 1.5, "y": 2.7})

		# Store the initial ID
		initial_id = initial_obj.get_primary_key()

		# Modify fields and generate new ID
		initial_obj.name = "Modified Object"
		initial_obj.number = 84
		initial_obj.colors.append(Color.GREEN)
		initial_obj.metadata["z"] = 3.9
		initial_obj.new_id()

		# Confirm ID has changed
		self.assertNotEqual(initial_id, initial_obj.get_primary_key())

		# Merge modified object
		data_engine.merge(initial_obj)

		# Query using the new ID
		queried_new = data_engine.query(ComplexObject).filter_by_id(initial_obj.get_primary_key())
		self.assertIsNotNone(queried_new)
		self.assertEqual(queried_new.name, "Modified Object")
		self.assertEqual(queried_new.number, 84)
		self.assertEqual(queried_new.date, datetime(2023, 7, 21, 12, 0))
		self.assertEqual(queried_new.colors[0], Color.RED)
		self.assertEqual(queried_new.colors[1], Color.BLUE)
		self.assertEqual(queried_new.colors[2], Color.GREEN)
		# self.assertEqual(queried_new.colors, [Color.RED, Color.BLUE, Color.GREEN])
		self.assertEqual(queried_new.metadata, {"x": 1.5, "y": 2.7, "z": 3.9})

		# Query using the original ID
		queried_original = data_engine.query(ComplexObject).filter_by_id(initial_id)
		self.assertIsNotNone(queried_original)
		self.assertEqual(queried_original.name, "Test Object")
		self.assertEqual(queried_original.number, 42)
		self.assertEqual(queried_original.date, datetime(2023, 7, 21, 12, 0))
		self.assertEqual(queried_original.colors[0], Color.RED)
		self.assertEqual(queried_original.colors[1], Color.BLUE)
		# self.assertEqual(queried_original.colors, [Color.RED, Color.BLUE])
		self.assertEqual(queried_original.metadata, {"x": 1.5, "y": 2.7})

		# Confirm we have two distinct objects in the database
		self.assertNotEqual(queried_new.get_primary_key(), queried_original.get_primary_key())
	
	def test_schema_evolution(self):
		DB_FILE = 'test_schema_evolution.db'

		# Delete the database if it exists
		if os.path.exists(DB_FILE):
			os.remove(DB_FILE)

		# Initial schema
		DATA1 = DATADecorator()

		@DATA1
		@dataclass
		class Person:
			name: str
			age: int

		@DATA1
		@dataclass
		class Book:
			title: str
			author: Person

		# Create initial data
		engine1 = SQLStorageEngine(f"sqlite:///{DB_FILE}", DATA1)
		author = Person(name="John Doe", age=30)
		book = Book(title="Sample Book", author=author)
		engine1.merge(book)

		# New schema with additional fields
		DATA2 = DATADecorator()

		@DATA2
		@dataclass
		class Person:
			name: str
			age: int
			email: str = field(default=None)

		@DATA2
		@dataclass
		class Book:
			title: str
			author: Person
			publication_year: int = field(default=None)

		# Create new engine with updated schema
		engine2 = SQLStorageEngine(f"sqlite:///{DB_FILE}", DATA2)

		# Query existing data
		queried_book = engine2.query(Book).filter_by_id(book.get_primary_key())

		# Assert existing data is preserved
		self.assertEqual(queried_book.title, "Sample Book")
		self.assertEqual(queried_book.author.name, "John Doe")
		self.assertEqual(queried_book.author.age, 30)

		# Assert new fields exist but are None for existing data
		self.assertTrue(hasattr(queried_book, 'publication_year'))
		self.assertTrue(hasattr(queried_book.author, 'email'))

		# Create new data with new fields
		new_author = Person(name="Jane Smith", age=28, email="jane@example.com")
		new_book = Book(title="New Book", author=new_author, publication_year=2023)
		engine2.merge(new_book)

		# Query new data
		queried_new_book = engine2.query(Book).filter_by_id(new_book.get_primary_key())

		# Assert new data is correctly stored and retrieved
		self.assertEqual(queried_new_book.title, "New Book")
		self.assertEqual(queried_new_book.author.name, "Jane Smith")
		self.assertEqual(queried_new_book.author.age, 28)
		self.assertEqual(queried_new_book.author.email, "jane@example.com")
		self.assertEqual(queried_new_book.publication_year, 2023)
if __name__ == '__main__':
	unittest.main()