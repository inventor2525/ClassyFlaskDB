from typing import List
from ClassyFlaskDB.DATA import *
from ClassyFlaskDB.serialization import JSONEncoder
import unittest

import json
from copy import deepcopy
from datetime import datetime, timedelta

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
			
	def test_relationship_with_manual_dataclass(self):
		DATA = DATADecorator(auto_decorate_as_dataclass = False)

		# Define the data classes
		@DATA
		@dataclass
		class Foe:
			name: str
			strength: int

		@DATA
		@dataclass
		class Bar:
			name: str
			location: str = field(default_factory=lambda:"hello world")
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
	
	def test_relationship_with_manual_dataclass(self):
		DATA = DATADecorator(auto_decorate_as_dataclass = False)

		# Define the data classes
		@DATA
		@dataclass
		class Foe:
			name: str
			strength: int

		@DATA
		@dataclass
		class Foe1(Foe):
			hit_points: int
			
		@DATA
		@dataclass
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
			self.assertEqual(queried_holder.chain_link.auto_id, chain_link1.auto_id)
			self.assertEqual(queried_holder.chain_link.next_link.auto_id, chain_link2.auto_id)
			self.assertEqual(queried_holder.chain_link.next_link.next_link.auto_id, chain_link3.auto_id)
			self.assertEqual(queried_holder.other, None)
			self.assertEqual(queried_holder.others, [])
			
			queried_holder.others.append(ChainLink(name='Link 4'))
			queried_holder.others.append(ChainLink(name='Link 5'))
			session.merge(queried_holder)
			session.commit()
		
		j3 = data_engine.to_json()
		print_DATA_json(j3)
		
		with data_engine.session() as session:
			queried_holder = session.query(Holder).first()
			self.assertEqual(queried_holder.others[0].name, 'Link 4')
			self.assertEqual(queried_holder.others[1].name, 'Link 5')
	
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
	
	def test_merge_with_shallow_update_and_nested_object_swap(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		class NestedObject:
			name: str
			value: int

		@DATA
		class ParentObject:
			title: str
			nested: NestedObject

		data_engine = DATAEngine(DATA)

		# Create and merge initial objects
		nested_obj1 = NestedObject(name="Initial Nested", value=100)
		parent_obj = ParentObject(title="Initial Parent", nested=nested_obj1)
		data_engine.merge(parent_obj)

		# Modify the parent object and merge with deeply=False
		parent_obj.title = "Modified Parent"
		data_engine.merge(parent_obj, deeply=False)

		# Query from database to verify changes
		with data_engine.session() as session:
			queried_parent = session.query(ParentObject).filter_by(title="Modified Parent").first()
			self.assertIsNotNone(queried_parent)
			self.assertEqual(queried_parent.title, "Modified Parent")
			self.assertEqual(queried_parent.nested.name, "Initial Nested")

		# Swap the nested object and merge again
		nested_obj2 = NestedObject(name="New Nested", value=200)
		parent_obj.nested = nested_obj2
		data_engine.add(nested_obj2)
		data_engine.merge(parent_obj, deeply=False)

		# Query from database to verify the swap
		with data_engine.session() as session:
			queried_parent = session.query(ParentObject).filter_by(title="Modified Parent").first()
			self.assertIsNotNone(queried_parent)
			self.assertEqual(queried_parent.nested.name, "New Nested")
			self.assertEqual(queried_parent.nested.value, 200)
	
	def test_merge_with_list_of_nested_objects(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		class NestedObject:
			name: str
			value: int

		@DATA
		class ParentObject:
			title: str
			nested_objects: List[NestedObject] = field(default_factory=list)

		data_engine = DATAEngine(DATA)

		# Create and merge initial objects
		nested_obj1 = NestedObject(name="Nested 1", value=100)
		nested_obj2 = NestedObject(name="Nested 2", value=200)
		parent_obj = ParentObject(title="Parent", nested_objects=[nested_obj1, nested_obj2])
		data_engine.merge(parent_obj)

		# Modify the list of nested objects and merge with deeply=False
		nested_obj3 = NestedObject(name="Nested 3", value=300)
		parent_obj.nested_objects.append(nested_obj3)
		data_engine.add(nested_obj3)
		data_engine.merge(parent_obj, deeply=False)

		# Query from database to verify changes
		with data_engine.session() as session:
			queried_parent = session.query(ParentObject).filter_by(title="Parent").first()
			self.assertIsNotNone(queried_parent)
			self.assertEqual(len(queried_parent.nested_objects), 2) # 2 because we merged with deeply=False, this is not ideal behavior but it is the current behavior
			self.assertEqual(queried_parent.nested_objects[0].name, "Nested 1")
			self.assertEqual(queried_parent.nested_objects[1].name, "Nested 2")
			# self.assertEqual(queried_parent.nested_objects[2].name, "Nested 3")
	
	def test_merge_with_date_field(self):
		DATA = DATADecorator()

		# Define the data classes
		@DATA
		class ParentObject:
			title: str
			created_at: datetime

		data_engine = DATAEngine(DATA)

		# Create and merge initial object with a specific datetime
		initial_datetime = datetime.now()
		parent_obj = ParentObject(title="Initial Parent", created_at=initial_datetime)
		data_engine.merge(parent_obj)  # Deep merge to add the object initially

		# Modify the datetime field and merge with deeply=False
		updated_datetime = initial_datetime + timedelta(days=1)
		parent_obj.created_at = updated_datetime
		data_engine.merge(parent_obj, deeply=False)

		# Query from database to verify the datetime update
		with data_engine.session() as session:
			queried_parent = session.query(ParentObject).filter_by(title="Initial Parent").first()
			self.assertIsNotNone(queried_parent)
			self.assertEqual(queried_parent.created_at, updated_datetime)
	
	def test_hash_id_cascade(self):
		DATA = DATADecorator()

		@DATA(generated_id_type=ID_Type.HASHID)
		class InnerObject:
			value: str

		@DATA(generated_id_type=ID_Type.HASHID)
		class MiddleObject:
			inner: InnerObject
			value: str

		@DATA(generated_id_type=ID_Type.HASHID)
		class TopObject:
			middle: MiddleObject
			value: str

		data_engine = DATAEngine(DATA)

		inner_obj = InnerObject(value="Inner Value")
		middle_obj = MiddleObject(inner=inner_obj, value="Middle Value")
		top_obj = TopObject(middle=middle_obj, value="Top Value")
		
		inner_obj.new_id()
		middle_obj.new_id()
		top_obj.new_id()

		# Initial IDs
		initial_top_id = top_obj.auto_id
		initial_middle_id = middle_obj.auto_id
		initial_inner_id = inner_obj.auto_id

		# Change a field on the innermost object
		inner_obj.value = "New Inner Value"

		# Call new_id() on the topmost object
		top_obj.new_id()
		new_top_id = top_obj.auto_id
		new_middle_id = middle_obj.auto_id
		new_inner_id = inner_obj.auto_id

		# Verify that all IDs have stayed the same
		self.assertEqual(initial_top_id, new_top_id)
		self.assertEqual(initial_middle_id, new_middle_id)
		self.assertEqual(initial_inner_id, new_inner_id)
		
		# Call new_id(True) on the topmost object
		top_obj.new_id(True)
		new_top_id = top_obj.auto_id
		new_middle_id = middle_obj.auto_id
		new_inner_id = inner_obj.auto_id

		# Verify that all IDs have changed
		self.assertNotEqual(initial_top_id, new_top_id)
		self.assertNotEqual(initial_middle_id, new_middle_id)
		self.assertNotEqual(initial_inner_id, new_inner_id)

		# Call new_id() again on the topmost object
		top_obj.new_id(True)
		same_top_id = top_obj.auto_id
		same_middle_id = middle_obj.auto_id
		same_inner_id = inner_obj.auto_id

		# Verify that the IDs haven't changed
		self.assertEqual(new_top_id, same_top_id)
		self.assertEqual(new_middle_id, same_middle_id)
		self.assertEqual(new_inner_id, same_inner_id)
		
	def test_object_source_sourced_object(self):
		DATA = DATADecorator()

		@DATA
		class Object:
			created_at: datetime = field(default_factory=datetime.utcnow, kw_only=True)

		@DATA
		class Source(Object):
			tag: str = field(default=None, kw_only=True)  # Making tag a non-default field while keeping the dataclass happy

		@DATA
		class SourcedObject(Object):
			source: Source = field(default=None, kw_only=True)  # Including source as an optional field

		data_engine = DATAEngine(DATA)

		# Create some fake data
		source1 = Source(tag="Source 1")
		source2 = Source(tag="Source 2")

		obj1 = SourcedObject(created_at=datetime(2022, 1, 1), source=source1)
		obj2 = SourcedObject(created_at=datetime(2022, 1, 15), source=source2)
		obj3 = SourcedObject(created_at=datetime(2022, 2, 1), source=source1)

		data_engine.merge(obj1)
		data_engine.merge(obj2)
		data_engine.merge(obj3)

		# Query from database
		with data_engine.session() as session:
			queried_objects = session.query(SourcedObject).all()

			self.assertEqual(len(queried_objects), 3)

			for obj in queried_objects:
				if obj.created_at == datetime(2022, 1, 1):
					self.assertEqual(obj.source.tag, "Source 1")
				elif obj.created_at == datetime(2022, 1, 15):
					self.assertEqual(obj.source.tag, "Source 2")
				elif obj.created_at == datetime(2022, 2, 1):
					self.assertEqual(obj.source.tag, "Source 1")
					
	def test_datetime_fields_with_inheritance(self):
		DATA = DATADecorator(auto_decorate_as_dataclass=False)
		
		@DATA
		@dataclass
		class Object:
			date_created: datetime = field(
				default_factory=datetime.utcnow, kw_only=True, 
				metadata={"no_update":True}
			)
		
		@DATA
		@dataclass
		class SubClass(Object):
			name:str
			
		@DATA
		@dataclass
		class SubSubClass(SubClass):
			description:str
			
		@DATA
		@dataclass
		class SubSubSubClass(SubSubClass):
			something:str
		
		engine = DATAEngine(DATA)
		
		sc1 = SubSubSubClass("hello", "Why do", "How are")
		sc2 = SubSubSubClass("world!", "this?", "You?")
		
		self.assertEqual(SubClass.from_json(sc1.to_json()).name, sc1.name)
		self.assertEqual(SubClass.from_json(sc2.to_json()).name, sc2.name)
		
		for table_name, table_contents in sc1.to_json()['obj'].items():
			if len(table_contents)==0:
				continue
			if table_name == "Object_Table":
				self.assertTrue("date_created__DateTimeObj" in table_contents[0])
				self.assertTrue("date_created__TimeZone" in table_contents[0])
			else:
				self.assertTrue("date_created__DateTimeObj" not in table_contents[0])
				self.assertTrue("date_created__TimeZone" not in table_contents[0])
						
	def test_sourced_objects(self):
		DATA = DATADecorator()

		@DATA
		class Object:
			date_created: datetime = field(default_factory=datetime.utcnow, kw_only=True)
			
		@DATA
		class Tag(Object):
			key: str = field(kw_only=True)

		@DATA
		class Source(Object):
			source_name: str = field(kw_only=True)

		@DATA
		class SourcedObject(Object):
			source: Source = field(kw_only=True)
			tags: List[Tag] = field(default_factory=list, kw_only=True)

		data_engine = DATAEngine(DATA)

		# Create some fake data
		source = Source(source_name="Fake Source")
		tag1 = Tag(key="tag1")
		tag2 = Tag(key="tag2")
		sourced_object = SourcedObject(source=source, tags=[tag1, tag2])

		data_engine.merge(sourced_object)

		# Query from database
		with data_engine.session() as session:
			queried_object = session.query(SourcedObject).first()

			self.assertIsNotNone(queried_object)
			self.assertEqual(queried_object.source.source_name, "Fake Source")
			self.assertEqual(len(queried_object.tags), 2)
			self.assertEqual(queried_object.tags[0].key, "tag1")
			self.assertEqual(queried_object.tags[1].key, "tag2")
			
	def test_frozen_dates_with_forward_ref_sourced_objects(self):
		DATA = DATADecorator(auto_decorate_as_dataclass=False)

		@DATA
		@dataclass
		class Object:
			date_created: datetime = field(
				default_factory=datetime.utcnow, kw_only=True, 
				metadata={"no_update":True}
			)
			source: "Object" = field(default=None, kw_only=True)
			tags: List["Tag"] = field(default_factory=list, kw_only=True)
			
		@DATA(generated_id_type=ID_Type.HASHID, hashed_fields=["key"])
		@dataclass
		class Tag(Object):
			key: str

		@DATA(generated_id_type=ID_Type.HASHID, hashed_fields=["class_name"])
		@dataclass
		class Source(Object):
			class_name: str
			
		@DATA(generated_id_type=ID_Type.HASHID, hashed_fields=["name"])
		@dataclass
		class HashedKeyObj(Object):
			name: str = field(kw_only=True)

		data_engine = DATAEngine(DATA)
		
		source_name = "DATA class unit test"
		source = Source(source_name)
		tag1 = Tag(key="A first tag", source=source)
		tag2 = Tag(key="A second tag", source=source)
		hk_obj = HashedKeyObj(name="My HK Obj", source=source, tags=[tag1, tag2])
		
		data_engine.merge(hk_obj)
		
		#Ensure we're querying correctly:
		with data_engine.session() as session:
			queried_hk:HashedKeyObj = session.query(HashedKeyObj).first()
			self.assertEquals(queried_hk.source.class_name, source_name)
			self.assertEquals(queried_hk.date_created, hk_obj.date_created)
			self.assertEquals(queried_hk.source.date_created, hk_obj.source.date_created)
			self.assertEquals(len(queried_hk.tags), 2)
			self.assertEquals(queried_hk.tags[0].source.class_name, source_name)
			self.assertEquals(queried_hk.tags[0].key, "A first tag")
			self.assertEquals(queried_hk.tags[0].date_created, tag1.date_created)
			
			self.assertEquals(queried_hk.tags[1].source.class_name, source_name)
			self.assertEquals(queried_hk.tags[1].key, "A second tag")
			self.assertEquals(queried_hk.tags[1].date_created, tag2.date_created)
		
		#Create new objects with id's that should be the same as the originals:
		new_source = Source(source_name)
		new_tag1 = Tag(key="A first tag", source=new_source)
		new_tag2 = Tag(key="A second tag", source=new_source)
		new_hk = HashedKeyObj(name="My HK Obj", source=new_source, tags=[new_tag1, new_tag2])
		
		#Test that they have the same id's:
		self.assertEquals(new_hk.get_primary_key(), hk_obj.get_primary_key())
		self.assertEquals(new_tag1.get_primary_key(), tag1.get_primary_key())
		self.assertEquals(new_tag2.get_primary_key(), tag2.get_primary_key())
		
		print(json.dumps(data_engine.to_json(), indent=4, cls=JSONEncoder))
		data_engine.merge(new_hk)
		print(json.dumps(data_engine.to_json(), indent=4, cls=JSONEncoder))
		
		# Verify that no_update took effect and that the dates
		# have not been changed, even though we merged new objects:
		with data_engine.session() as session:
			queried_hk2:HashedKeyObj = session.query(HashedKeyObj).first()
			self.assertEquals(queried_hk2.date_created, hk_obj.date_created)
			self.assertEquals(queried_hk2.source.get_primary_key(), hk_obj.source.get_primary_key())
			self.assertEquals(queried_hk2.source.date_created, hk_obj.source.date_created)
			self.assertEquals(queried_hk2.tags[0].date_created, tag1.date_created)
			self.assertEquals(queried_hk2.tags[1].date_created, tag2.date_created)
		
			
if __name__ == '__main__':
	unittest.main()