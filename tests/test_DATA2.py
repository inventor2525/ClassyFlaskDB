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
class Foe:
	name: str
	strength: int

@DATA
class Bar:
	name: str
	location: str
	foes: List[Foe] = field(default_factory=list)

class DATA_Decorator2(unittest.TestCase):
	def test_list_relationship(self):
		# Create an in-memory SQLite database
		engine = create_engine('sqlite:///:memory:')

		# Finalize the mapping
		DATA.finalize(engine, globals()).metadata.create_all(engine)

		# Create a session
		Session = sessionmaker(bind=engine)
		session = Session()

		foe1 = Foe(name="Dragon1", strength=100)
		foe2 = Foe(name="Dragon2", strength=200)
		foe3 = Foe(name="Dragon2", strength=200)
		bar = Bar(name="Dragon's Lair", location="Mountain", foes=[foe1, foe2, foe3])

		# Insert into database
		session.add(bar)
		session.commit()

		# Query from database
		queried_bar = session.query(Bar).filter_by(name="Dragon's Lair").first()

		# Validate
		self.assertEqual(queried_bar.name, bar.name)
		self.assertEqual(queried_bar.location, bar.location)

		for i in range(3):
			self.assertEqual(queried_bar.foes[i].name, bar.foes[i].name)
			self.assertEqual(queried_bar.foes[i].strength, bar.foes[i].strength)

		session.close()

if __name__ == '__main__':
	unittest.main()