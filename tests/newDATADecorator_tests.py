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
		data_engine.merge(bar)

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
		
if __name__ == '__main__':
	unittest.main()