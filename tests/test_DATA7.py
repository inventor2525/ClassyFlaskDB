from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from ClassyFlaskDB.DATA import DATADecorator
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

class DATA_Decorator7(unittest.TestCase):
	def test_relationship_with_circular_ref_and_no_globals(self):
		# Create an in-memory SQLite database
		engine = create_engine('sqlite:///:memory:')

		# Finalize the mapping
		DATA.finalize(engine)

		# Create a session
		Session = sessionmaker(bind=engine)
		session = Session()

		foe = Foe(name="Dragon1", strength=100)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe)

		foe.bar = bar

		# Insert into database
		session.add(bar)
		session.commit()

		# Query from database
		queried_bar = session.query(Bar).filter_by(name="Dragon's Lair").first()

		# Validate
		self.assertEqual(queried_bar.name, bar.name)
		self.assertEqual(queried_bar.location, bar.location)
		
		self.assertEqual(queried_bar.foe.name, bar.foe.name)
		self.assertEqual(queried_bar.foe.strength, bar.foe.strength)

		self.assertEqual(queried_bar.foe.bar.name, bar.name)
		self.assertEqual(queried_bar.foe.bar.location, bar.location)
		self.assertEqual(queried_bar.foe.bar.uuid, bar.uuid)

		session.close()

if __name__ == '__main__':
	unittest.main()