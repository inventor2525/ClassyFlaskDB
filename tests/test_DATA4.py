from ClassyFlaskDB.DATA import *
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
	foes: List[Foe] = field(default_factory=list)

class DATA_Decorator3(unittest.TestCase):
	def test_list_relationship_with_circular_ref(self):
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

if __name__ == '__main__':
	unittest.main()