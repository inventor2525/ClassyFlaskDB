from ClassyFlaskDB.new.SQLStorageEngine import *
import unittest
from enum import Enum

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
			
		data_engine = SQLAlchemyStorageEngine("sqlite:///:memory:", transcoder_collection, DATA)
		
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

		data_engine = SQLAlchemyStorageEngine("sqlite:///:memory:", transcoder_collection, DATA)

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
				
			data_engine = SQLAlchemyStorageEngine("sqlite:///:memory:", transcoder_collection, DATA)

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
		
	def test_list_and_circular_ref(self):
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

		data_engine = SQLAlchemyStorageEngine("sqlite:///:memory:", transcoder_collection, DATA)

		# Create family members
		alice = Person("Alice", 10)
		bob = Person("Bob", 12)
		eve = Person("Eve", 35)
		adam = Person("Adam", 37)

		# Create family
		family = ImmediateFamily("Smith", [alice, bob], [eve, adam])

		# Set circular references
		alice.family = family
		bob.family = family
		eve.family = family
		adam.family = family

		# Merge into database
		data_engine.merge(family)

		# Query from database
		queried_family = data_engine.query(ImmediateFamily).filter_by_id(family.get_primary_key())

		# Validate
		self.assertEqual(queried_family.surname, "Smith")
		self.assertEqual(len(queried_family.children), 2)
		self.assertEqual(len(queried_family.parents), 2)

		alice_queried = queried_family.children[0]
		bob_queried = queried_family.children[1]
		eve_queried = queried_family.parents[0]
		adam_queried = queried_family.parents[1]

		self.assertEqual(alice_queried.name, "Alice")
		self.assertEqual(bob_queried.name, "Bob")
		self.assertEqual(eve_queried.name, "Eve")
		self.assertEqual(adam_queried.name, "Adam")

		# Check circular references
		self.assertEqual(alice_queried.family.surname, "Smith")
		self.assertEqual(bob_queried.family.surname, "Smith")
		self.assertEqual(eve_queried.family.surname, "Smith")
		self.assertEqual(adam_queried.family.surname, "Smith")

		# Check that circular references are maintained
		self.assertIs(alice_queried.family, queried_family)
		self.assertIs(bob_queried.family, queried_family)
		self.assertIs(eve_queried.family, queried_family)
		self.assertIs(adam_queried.family, queried_family)
	
	def test_dictionary(self):
		DATA = DATADecorator()

		@DATA
		@dataclass
		class DictContainer:
			name: str
			data: Dict[str, int]

		data_engine = SQLAlchemyStorageEngine("sqlite:///:memory:", transcoder_collection, DATA)

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

		data_engine = SQLAlchemyStorageEngine("sqlite:///:memory:", transcoder_collection, DATA)

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
		eve_family = ImmediateFamily("Eve's Maiden", [], [gma_eve, gpa_eve], [])
		adam_family = ImmediateFamily("Adam's Maiden", [], [gma_adam, gpa_adam], [])

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
		data_engine.merge(smith_family)
		data_engine.merge(eve_family)
		data_engine.merge(adam_family)

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
		self.assertEqual(eve_queried.family.parents[0].name, gma_eve_queried.name)
		self.assertEqual(eve_queried.family.parents[1].name, gpa_eve_queried.name)
		self.assertEqual(adam_queried.family.parents[0].name, gma_adam_queried.name)
		self.assertEqual(adam_queried.family.parents[1].name, gpa_adam_queried.name)

		# Check object identity
		self.assertIs(eve_queried.family.parents[0], gma_eve_queried)
		self.assertIs(eve_queried.family.parents[1], gpa_eve_queried)
		self.assertIs(adam_queried.family.parents[0], gma_adam_queried)
		self.assertIs(adam_queried.family.parents[1], gpa_adam_queried)

if __name__ == '__main__':
	unittest.main()