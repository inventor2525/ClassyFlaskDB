from typing import List
from ClassyFlaskDB.DATA import *
from ClassyFlaskDB.serialization import JSONEncoder
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
			print(json.dumps(data_engine.to_json(), indent=4, cls=JSONEncoder))
			self.assertEqual(queried_bar.foe.hit_points, foe1.hit_points)
	
	def test_to_json(self):
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
		
		@DATA
		class ChainLink:
			name: str
			next_link: "ChainLink" = None
			
		@DATA
		class Holder:
			bar: Bar
			chain_link: ChainLink
		data_engine = DATAEngine(DATA, engine_str='sqlite:///my_database_test.db')
		
		foe = Foe(name="Dragon", strength=100)
		bar = Bar(name="Dragon's Lair", location="Mountain", foe=foe)
		
		chain_link1 = ChainLink(name="Link 1")
		chain_link2 = ChainLink(name="Link 2")
		chain_link3 = ChainLink(name="Link 3")
		chain_link1.next_link = chain_link2
		chain_link2.next_link = chain_link3
		
		holder = Holder(bar=bar, chain_link=chain_link1)
		data_engine.merge(holder)
		
		def print_holder(holder, step_name):
			print(step_name)
			print(holder.bar.name)
			print(holder.chain_link.name)
			print(holder.chain_link.next_link.name)
			print(holder.chain_link.next_link.next_link.name)
			print(holder.chain_link.next_link.next_link.next_link)
		print_holder(holder, "Original")
		holder_json = holder.to_json()
		print_holder(holder, "After to_json")
		
		print_DATA_json(holder_json)
		
		holder2 = Holder.from_json(holder_json)
		print_holder(holder2, "loaded from_json")
		
		self.assertEqual(holder2.bar.name, holder.bar.name)
		self.assertEqual(holder2.bar.location, holder.bar.location)
		self.assertEqual(holder2.bar.foe.name, holder.bar.foe.name)
		self.assertEqual(holder2.bar.foe.strength, holder.bar.foe.strength)
		
		self.assertEqual(holder2.chain_link.name, holder.chain_link.name)
		self.assertEqual(holder2.chain_link.next_link.name, holder.chain_link.next_link.name)
		self.assertEqual(holder2.chain_link.next_link.next_link.name, holder.chain_link.next_link.next_link.name)
		self.assertEqual(holder2.chain_link.next_link.next_link.next_link, None)
		
	def test_to_json_small(self):
		DATA = DATADecorator()

		@DATA
		class ChainLink:
			name: str
			next_link: 'ChainLink' = None

		@DATA
		class Holder:
			chain_link: ChainLink

		data_engine = DATAEngine(DATA)
		
		chain_link1 = ChainLink(name='Link 1')
		chain_link2 = ChainLink(name='Link 2')
		chain_link3 = ChainLink(name='Link 3')
		chain_link1.next_link = chain_link2
		chain_link2.next_link = chain_link3
		holder = Holder(chain_link=chain_link1)

		holder_json = holder.to_json()
		print_DATA_json(holder_json)
		
		self.assertEqual(holder_json['type'], 'Holder')
		self.assertEqual(holder_json['primary_key'], holder.auto_id)
		self.assertEqual(len(holder_json['obj']['Holder_Table']), 1)
		self.assertEqual(len(holder_json['obj']['ChainLink_Table']), 3)
		self.assertEqual(holder_json['obj']['Holder_Table'][0]['auto_id'], holder.auto_id)
		self.assertEqual(holder_json['obj']['Holder_Table'][0]['chain_link_fk'], chain_link1.auto_id)
		self.assertEqual(holder_json['obj']['ChainLink_Table'][0]['auto_id'], chain_link1.auto_id)
		self.assertEqual(holder_json['obj']['ChainLink_Table'][0]['name'], chain_link1.name)
		self.assertEqual(holder_json['obj']['ChainLink_Table'][0]['next_link_fk'], chain_link2.auto_id)
		self.assertEqual(holder_json['obj']['ChainLink_Table'][1]['auto_id'], chain_link2.auto_id)
		self.assertEqual(holder_json['obj']['ChainLink_Table'][1]['name'], chain_link2.name)
		self.assertEqual(holder_json['obj']['ChainLink_Table'][1]['next_link_fk'], chain_link3.auto_id)
		self.assertEqual(holder_json['obj']['ChainLink_Table'][2]['auto_id'], chain_link3.auto_id)
		self.assertEqual(holder_json['obj']['ChainLink_Table'][2]['name'], chain_link3.name)
		self.assertEqual(holder_json['obj']['ChainLink_Table'][2]['next_link_fk'], None)
		
	def test_adding_a_table(self):
		#Remove the test database if it exists
		import os
		if os.path.exists("test_adding_a_table.db"):
			os.remove("test_adding_a_table.db")
			
		DATA = DATADecorator()

		@DATA
		class ChainLink:
			name: str
			next_link: 'ChainLink' = None

		@DATA
		class Holder:
			chain_link: ChainLink

		data_engine = DATAEngine(DATA, engine_str='sqlite:///test_adding_a_table.db')
		
		chain_link1 = ChainLink(name='Link 1')
		chain_link2 = ChainLink(name='Link 2')
		chain_link3 = ChainLink(name='Link 3')
		chain_link1.next_link = chain_link2
		chain_link2.next_link = chain_link3
		holder = Holder(chain_link=chain_link1)
		
		data_engine.merge(holder)
		j1 = data_engine.to_json()
		data_engine.dispose()
		
		@DATA
		class ANewTable:
			name: str
			holder: Holder = None
		
		data_engine = DATAEngine(DATA, engine_str='sqlite:///test_adding_a_table.db')
		
		thing = ANewTable(name='thing', holder=holder)
		data_engine.merge(thing)
		j2 = data_engine.to_json()
		
		self.assertEqual(j1["ChainLink_Table"], j2["ChainLink_Table"])
		self.assertEqual(j1["Holder_Table"], j2["Holder_Table"])
		
		self.assertEqual("ANewTable_Table" in j2, True)
		self.assertEqual("ANewTable_Table" in j1, False)
		print_DATA_json(j1)
		print_DATA_json(j2)
		
		with data_engine.session() as session:
			queried_thing = session.query(ANewTable).filter_by(name='thing').first()
			self.assertEqual(queried_thing.auto_id, thing.auto_id)
			self.assertEqual(queried_thing.name, thing.name)
			self.assertEqual(queried_thing.holder.auto_id, holder.auto_id)
			self.assertEqual(queried_thing.holder.chain_link.auto_id, chain_link1.auto_id)
			self.assertEqual(queried_thing.holder.chain_link.name, chain_link1.name)
	
	def test_adding_a_column(self):
		#Remove the test database if it exists
		import os
		if os.path.exists("test_adding_a_column.db"):
			os.remove("test_adding_a_column.db")
			
		DATA = DATADecorator()

		@DATA
		class ChainLink:
			name: str
			next_link: 'ChainLink' = None

		@DATA
		class Holder:
			chain_link: ChainLink

		data_engine = DATAEngine(DATA, engine_str='sqlite:///test_adding_a_column.db')
		
		chain_link1 = ChainLink(name='Link 1')
		chain_link2 = ChainLink(name='Link 2')
		chain_link3 = ChainLink(name='Link 3')
		chain_link1.next_link = chain_link2
		chain_link2.next_link = chain_link3
		holder = Holder(chain_link=chain_link1)
		
		data_engine.merge(holder)
		j1 = data_engine.to_json()
		data_engine.dispose()
		
		DATA = DATADecorator()

		@DATA
		class ChainLink:
			name: str
			next_link: 'ChainLink' = None

		@DATA
		class Holder:
			chain_link: ChainLink
			a_new_column: str
		
		data_engine = DATAEngine(DATA, engine_str='sqlite:///test_adding_a_column.db', should_backup=False)
		
		j2 = data_engine.to_json()
		
		self.assertEqual(j1["ChainLink_Table"], j2["ChainLink_Table"])
		# self.assertEqual(j1["Holder_Table"], j2["Holder_Table"])
		
		print_DATA_json(j1)
		print_DATA_json(j2)
		
		with data_engine.session() as session:
			queried_holder = session.query(Holder).first()
			self.assertEqual(holder.auto_id, queried_holder.auto_id)
			
	def test_adding_columns_with_fks(self):
		#Remove the test database if it exists
		import os
		if os.path.exists("test_adding_columns_with_fks.db"):
			os.remove("test_adding_columns_with_fks.db")
			
		DATA = DATADecorator()

		@DATA
		class ChainLink:
			name: str
			next_link: 'ChainLink' = None

		@DATA
		class Holder:
			chain_link: ChainLink

		data_engine = DATAEngine(DATA, engine_str='sqlite:///test_adding_columns_with_fks.db')
		
		chain_link1 = ChainLink(name='Link 1')
		chain_link2 = ChainLink(name='Link 2')
		chain_link3 = ChainLink(name='Link 3')
		chain_link1.next_link = chain_link2
		chain_link2.next_link = chain_link3
		holder = Holder(chain_link=chain_link1)
		
		data_engine.merge(holder)
		j1 = data_engine.to_json()
		data_engine.dispose()
		
		DATA = DATADecorator()

		@DATA
		class ChainLink:
			name: str
			next_link: 'ChainLink' = None

		@DATA
		class Holder:
			chain_link: ChainLink
			other: Holder = None
			others: List[ChainLink] = field(default_factory=list)
		
		data_engine = DATAEngine(DATA, engine_str='sqlite:///test_adding_columns_with_fks.db', should_backup=False)
		
		j2 = data_engine.to_json()
		
		self.assertEqual(j1["ChainLink_Table"], j2["ChainLink_Table"])
		# self.assertEqual(j1["Holder_Table"], j2["Holder_Table"])
		
		print_DATA_json(j1)
		print_DATA_json(j2)
		
		with data_engine.session() as session:
			queried_holder = session.query(Holder).first()
			self.assertEqual(holder.auto_id, queried_holder.auto_id)
	
	def test_unmapped_dataclass_field_initialization(self):
		DATA = DATADecorator()
		
		class UnmappedType:
			def __init__(self, value="default"):
				self.value = value
		
		@DATA
		class Example:
			mapped_field: str  # This field is mapped to the database
			unmapped_field: UnmappedType = field(default_factory=lambda: UnmappedType("custom_default"), init=False)  # Unmapped custom type with a default factory

		data_engine = DATAEngine(DATA)
		
		# Create an instance with only the mapped field
		example = Example(mapped_field="Test")
		self.assertEqual(example.mapped_field, "Test")
		self.assertTrue(hasattr(example, 'unmapped_field'))
		self.assertIsInstance(example.unmapped_field, UnmappedType)
		self.assertEqual(example.unmapped_field.value, "custom_default")
		
		data_engine.merge(example)
		
		# Query from database
		with data_engine.session() as session:
			queried_example = session.query(Example).filter_by(mapped_field="Test").first()

			# Validate that the unmapped field is initialized correctly
			self.assertEqual(queried_example.mapped_field, example.mapped_field)
			self.assertTrue(hasattr(queried_example, 'unmapped_field'))
			self.assertIsInstance(queried_example.unmapped_field, UnmappedType)
			self.assertEqual(queried_example.unmapped_field.value, "custom_default")
		
	def test_enums(self):
		DATA = DATADecorator()
		
		from enum import Enum
		
		class Color(Enum):
			RED = 1
			GREEN = 2
			BLUE = 3
		
		class Size(Enum):
			SMALL = "small"
			MEDIUM = "medium"
			LARGE = "large"
			
		# Define the data classes
		@DATA
		class Foe:
			name: str
			strength: int
			color: Color
			size: Size
			
		data_engine = DATAEngine(DATA)
		
		foe = Foe(name="Dragon", strength=100, color=Color.GREEN, size=Size.MEDIUM)

		data_engine.merge(foe)
		
		# Query from database
		with data_engine.session() as session:
			queried_foe = session.query(Foe).filter_by(name="Dragon").first()

			# Validate
			self.assertEqual(queried_foe.name, foe.name)
			self.assertEqual(queried_foe.strength, foe.strength)
			self.assertEqual(queried_foe.color, foe.color)
			self.assertEqual(type(queried_foe.color), type(foe.color))
			self.assertEqual(queried_foe.size, foe.size)
			self.assertEqual(type(queried_foe.size), type(foe.size))
			#Notes on how to make this pass:
			#dataclass type will have to be loaded first, then it's value populated by sql alchamy since it wont know the enum type
			
if __name__ == '__main__':
	unittest.main()