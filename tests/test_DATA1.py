from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from ClassyFlaskDB.DATA import DATADecorator
from dataclasses import field
from typing import List
import unittest
from ClassyFlaskDB.helpers.resolve_type import TypeResolver

DATA = DATADecorator() #Re-define the DATA decorator since having only 1 accross all tests causes issues

# Define the data classes
@DATA
class Foe1:
	name: str
	strength: int

@DATA
class Bar1:
	name: str
	location: str
	foe: Foe1 = None
	
class DATA_Decorator1(unittest.TestCase):
	def test_relationship(self):
		# Create an in-memory SQLite database
		engine = create_engine('sqlite:///:memory:')

		# Finalize the mapping
		DATA.finalize(engine, globals()).metadata.create_all(engine)

		# Create a session
		Session = sessionmaker(bind=engine)
		session = Session()

		foe = Foe1(name="Dragon", strength=100)
		bar = Bar1(name="Dragon's Lair", location="Mountain", foe=foe)

		# Insert into database
		session.add(bar)
		session.commit()

		# Query from database
		queried_bar = session.query(Bar1).filter_by(name="Dragon's Lair").first()

		# Validate
		self.assertEqual(queried_bar.name, bar.name)
		self.assertEqual(queried_bar.location, bar.location)
		self.assertEqual(queried_bar.foe.name, foe.name)
		self.assertEqual(queried_bar.foe.strength, foe.strength)

		session.close()

if __name__ == '__main__':
	unittest.main()