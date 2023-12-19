from typing import List
from ClassyFlaskDB.DATA import *
from ClassyFlaskDB.Flaskify.serialization import FlaskifyJSONEncoder
import unittest

import json
from copy import deepcopy
	
class DATADecorator_tests(unittest.TestCase):
	def test_relationship(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		class Foe:
			name: str
			strength: int

		@DATA
		class Bar:
			name: str
			location: str
			foe: Foe = None
			
		data_engine = DATAEngine(DATA)
		
		foe = Foe(name="Dragon", strength=100)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe)

		data_engine.merge(bar)
		
		# Query from database
		with data_engine.session() as session:
			queried_bar = session.query(Bar).filter_by(name="Dragon's Lair").first()

			# Validate
			self.assertEqual(queried_bar.name, bar.name)
			self.assertEqual(queried_bar.location, bar.location)
			self.assertEqual(queried_bar.foe.name, foe.name)
			self.assertEqual(queried_bar.foe.strength, foe.strength)
			
	def test_list_relationship(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		class Foe:
			name: str
			strength: int

		@DATA
		class Bar:
			name: str
			location: str
			foes: List[Foe] = field(default_factory=list)
			
		data_engine = DATAEngine(DATA)
		
		foe1 = Foe(name="Dragon1", strength=100)
		foe2 = Foe(name="Dragon2", strength=200)
		foe3 = Foe(name="Dragon2", strength=200)
		bar = Bar(name="Dragon's Lair", location="Mountain", foes=[foe1, foe2, foe3])

		data_engine.merge(bar)
		
		# Query from database
		with data_engine.session() as session:
			queried_bar = session.query(Bar).filter_by(name="Dragon's Lair").first()

			# Validate
			self.assertEqual(queried_bar.name, bar.name)
			self.assertEqual(queried_bar.location, bar.location)

			for i in range(3):
				self.assertEqual(queried_bar.foes[i].name, bar.foes[i].name)
				self.assertEqual(queried_bar.foes[i].strength, bar.foes[i].strength)
				
	def test_relationship_with_forward_ref(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		class Bar:
			name: str
			location: str
			foe: "Foe" = None

		@DATA
		class Foe:
			name: str
			strength: int
			
		data_engine = DATAEngine(DATA)

		foe = Foe(name="Dragon", strength=100)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe)

		# Insert into database
		data_engine.add(bar)

		# Query from database
		with data_engine.session() as session:
			queried_bar = session.query(Bar).filter_by(name="Dragon's Lair").first()

			# Validate
			self.assertEqual(queried_bar.name, bar.name)
			self.assertEqual(queried_bar.location, bar.location)
			self.assertEqual(queried_bar.foe.name, foe.name)
			self.assertEqual(queried_bar.foe.strength, foe.strength)
			
	def test_list_relationship_with_circular_ref(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		class Foe:
			name: str
			strength: int
			bar: "Bar" = None

		@DATA
		class Bar:
			name: str
			location: str
			foes: List[Foe] = field(default_factory=list)
		
		data_engine = DATAEngine(DATA)
		
		foe1 = Foe(name="Dragon1", strength=100)
		foe2 = Foe(name="Dragon2", strength=200)
		foe3 = Foe(name="Dragon2", strength=200)
		bar = Bar(name="Dragon's Lair", location="Mountain", foes=[foe1, foe2, foe3])

		foe1.bar = bar
		foe2.bar = bar
		foe3.bar = bar

		# Insert into database
		data_engine.add(bar)

		# Query from database
		with data_engine.session() as session:
			queried_bar = session.query(Bar).filter_by(name="Dragon's Lair").first()

			# Validate
			self.assertEqual(queried_bar.name, bar.name)
			self.assertEqual(queried_bar.location, bar.location)

			for i in range(3):
				self.assertEqual(queried_bar.foes[i].name, bar.foes[i].name)
				self.assertEqual(queried_bar.foes[i].strength, bar.foes[i].strength)
	
	def test_relationship_with_circular_ref(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		class Foe:
			name: str
			strength: int
			bar: "Bar" = None

		@DATA
		class Bar:
			name: str
			location: str
			foe: "Foe" = None
			
		data_engine = DATAEngine(DATA)

		foe = Foe(name="Dragon1", strength=100)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe)

		foe.bar = bar

		# Insert into database
		data_engine.add(bar)

		# Query from database
		with data_engine.session() as session:
			queried_bar = session.query(Bar).filter_by(name="Dragon's Lair").first()

			# Validate
			self.assertEqual(queried_bar.name, bar.name)
			self.assertEqual(queried_bar.location, bar.location)
			
			self.assertEqual(queried_bar.foe.name, bar.foe.name)
			self.assertEqual(queried_bar.foe.strength, bar.foe.strength)

			self.assertEqual(queried_bar.foe.bar.name, bar.name)
			self.assertEqual(queried_bar.foe.bar.location, bar.location)
			self.assertEqual(queried_bar.foe.bar.auto_id, bar.auto_id)
	
	def test_polymorphic_relationship(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		class Foe:
			name: str
			strength: int

		@DATA
		class Foe1(Foe):
			hit_points: int
			
		@DATA
		class Bar:
			name: str
			location: str
			foe: Foe = None
			
		data_engine = DATAEngine(DATA)
		
		foe1 = Foe1(name="Dragon", strength=100, hit_points=100)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe1)

		# Insert into database
		data_engine.merge(bar)

		# merge 2 times again to test for a polymorphic relationship bug that was found that would
		# cause a Unique key error for auto_id of a held child class (foe1 in this case)
		foe1 = Foe1(name="Dragon", strength=100, hit_points=100)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe1)

		# Insert into database
		data_engine.merge(deepcopy(bar))
		
		# Insert into database
		data_engine.merge(deepcopy(bar))

		# Query from database
		with data_engine.session() as session:
			queried_bar = session.query(Bar).filter_by(name="Dragon's Lair").first()

			# Validate
			self.assertEqual(queried_bar.name, bar.name)
			self.assertEqual(queried_bar.location, bar.location)

			# self.assertEqual(queried_bar.foe.auto_id, foe1.auto_id)
			self.assertEqual(queried_bar.foe.name, foe1.name)
			self.assertEqual(queried_bar.foe.strength, foe1.strength)
			print(json.dumps(data_engine.to_json(), indent=4, cls=FlaskifyJSONEncoder))
			self.assertEqual(queried_bar.foe.hit_points, foe1.hit_points)
			
if __name__ == '__main__':
	unittest.main()