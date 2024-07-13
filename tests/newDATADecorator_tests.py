from ClassyFlaskDB.new.SQLStorageEngine import *
import unittest

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
if __name__ == '__main__':
	unittest.main()