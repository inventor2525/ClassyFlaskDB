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
class Bar:
	name: str
	location: str
	foe: "Foe" = None

@DATA
class Foe:
	name: str
	strength: int

class DATA_Decorator2(unittest.TestCase):
	def test_relationship_with_forward_ref(self):
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

if __name__ == '__main__':
	unittest.main()