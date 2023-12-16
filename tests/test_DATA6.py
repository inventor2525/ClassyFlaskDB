from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from ClassyFlaskDB.DATA import DATADecorator, DATAEngine
from dataclasses import field
from typing import List
import unittest
from ClassyFlaskDB.helpers.resolve_type import TypeResolver
import json
from json import JSONEncoder
from copy import deepcopy
class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return JSONEncoder.default(self, obj)

DATA = DATADecorator() #Re-define the DATA decorator since having only 1 accross all tests causes issues

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
	
class DATA_Decorator6(unittest.TestCase):
	def test_polymorphic_relationship(self):
		data_engine = DATAEngine(DATA)
		
		foe1 = Foe1(name="Dragon", strength=100, hit_points=100)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe1)

		# Insert into database
		data_engine.merge(bar)

		# merge 2 times again to test for a polymorphic relationship bug that was found that would
		# cause a Unique key error for uuid of a held child class (foe1 in this case)
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

			# self.assertEqual(queried_bar.foe.uuid, foe1.uuid)
			self.assertEqual(queried_bar.foe.name, foe1.name)
			self.assertEqual(queried_bar.foe.strength, foe1.strength)
			print(json.dumps(data_engine.to_json(), indent=4, cls=DateTimeEncoder))
			self.assertEqual(queried_bar.foe.hit_points, foe1.hit_points)

if __name__ == '__main__':
	unittest.main()