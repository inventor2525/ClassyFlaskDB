from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from ClassyFlaskDB.DATA import DATADecorator, DATAEngine
from dataclasses import field
from typing import List
import unittest

DATA = DATADecorator() #Re-define the DATA decorator since having only 1 accross all tests causes issues

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

class DATA_Decorator3(unittest.TestCase):
	def test_relationship_with_circular_ref(self):
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
			self.assertEqual(queried_bar.foe.bar.uuid, bar.uuid)

if __name__ == '__main__':
	unittest.main()