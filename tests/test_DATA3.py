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
class Bar3:
	name: str
	location: str
	foe: "Foe3" = None

@DATA
class Foe3:
	name: str
	strength: int

class DATA_Decorator2(unittest.TestCase):
	def test_relationship_with_forward_ref(self):
		# Create an in-memory SQLite database
		engine = create_engine('sqlite:///:memory:')

		# Finalize the mapping
		DATA.finalize(engine, globals()).metadata.create_all(engine)

		# Create a session
		Session = sessionmaker(bind=engine)
		session = Session()

		foe = Foe3(name="Dragon", strength=100)
		bar = Bar3(name="Dragon's Lair", location="Mountain", foe=foe)

		# Insert into database
		session.add(bar)
		session.commit()

		# Query from database
		queried_bar = session.query(Bar3).filter_by(name="Dragon's Lair").first()

		# Validate
		self.assertEqual(queried_bar.name, bar.name)
		self.assertEqual(queried_bar.location, bar.location)
		self.assertEqual(queried_bar.foe.name, foe.name)
		self.assertEqual(queried_bar.foe.strength, foe.strength)

		session.close()

if __name__ == '__main__':
	unittest.main()