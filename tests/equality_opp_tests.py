from ClassyFlaskDB.new.DATADecorator import DATADecorator
from ClassyFlaskDB.new.JSONStorageEngine import JSONStorageEngine
from ClassyFlaskDB.new.SQLStorageEngine import SQLStorageEngine
from dataclasses import dataclass
from typing import List, Dict
import unittest
import os

class EqualityOperationTests(unittest.TestCase):
    def create_storage(self, DATA: DATADecorator, engine_type: int):
        if engine_type == 0:
            return JSONStorageEngine(
                storage_path="test_equality.json",
                data_decorator=DATA
            )
        else:
            return SQLStorageEngine("sqlite:///:memory:", DATA)
            
    def test_simple_object_equality(self):
        def setup_and_query(engine_type: int):
            DATA = DATADecorator()
            
            @DATA
            @dataclass
            class Leaf:
                name: str
            
            @DATA
            @dataclass
            class Node:
                name: str
                leaf: Leaf
            
            storage = self.create_storage(DATA, engine_type)
            leaf = Leaf("test_leaf")
            original = Node("test_node", leaf)
            storage.merge(original)
            
            queried = storage.query(Node).filter_by_id(original.get_primary_key())
            return original, queried
        
        for engine_type in range(2):
            original, queried = setup_and_query(engine_type)
            self.assertEqual(original, queried)
    
    def test_list_equality(self):
        def setup_and_query(engine_type: int):
            DATA = DATADecorator()
            
            @DATA
            @dataclass
            class Leaf:
                name: str
            
            @DATA
            @dataclass
            class NodeWithList:
                name: str
                leaves: List[Leaf]
            
            storage = self.create_storage(DATA, engine_type)
            leaves = [Leaf("leaf1"), Leaf("leaf2")]
            original = NodeWithList("test_node", leaves)
            storage.merge(original)
            
            queried = storage.query(NodeWithList).filter_by_id(original.get_primary_key())
            return original, queried
        
        for engine_type in range(2):
            original, queried = setup_and_query(engine_type)
            self.assertEqual(original, queried)
    
    def test_dict_equality(self):
        def setup_and_query(engine_type: int):
            DATA = DATADecorator()
            
            @DATA
            @dataclass
            class Leaf:
                name: str
            
            @DATA
            @dataclass
            class NodeWithDict:
                name: str
                leaves: Dict[str, Leaf]
            
            storage = self.create_storage(DATA, engine_type)
            leaves = {"a": Leaf("leaf1"), "b": Leaf("leaf2")}
            original = NodeWithDict("test_node", leaves)
            storage.merge(original)
            
            queried = storage.query(NodeWithDict).filter_by_id(original.get_primary_key())
            return original, queried
        
        for engine_type in range(2):
            original, queried = setup_and_query(engine_type)
            self.assertEqual(original, queried)
    
	# Equality with circular references fail due to infinite recursion, and are
    # not yet supported as they are written by dataclass and would need to be
    # explicitly re-implemented but are not currently used. :
    
    # def test_circular_ref_equality(self):
    #     def setup_and_query(engine_type: int):
    #         DATA = DATADecorator()
            
    #         @DATA
    #         @dataclass
    #         class NodeA:
    #             name: str
    #             other: 'NodeB' = None
            
    #         @DATA
    #         @dataclass
    #         class NodeB:
    #             name: str
    #             other: NodeA = None
            
    #         storage = self.create_storage(DATA, engine_type)
    #         node_a = NodeA("a")
    #         node_b = NodeB("b")
    #         node_a.other = node_b
    #         node_b.other = node_a
            
    #         storage.merge(node_a)
    #         queried = storage.query(NodeA).filter_by_id(node_a.get_primary_key())
    #         return node_a, queried
        
    #     for engine_type in range(2):
    #         original, queried = setup_and_query(engine_type)
    #         self.assertEqual(original, queried)
    
    # def test_circular_ref_dict_equality(self):
    #     def setup_and_query(engine_type: int):
    #         DATA = DATADecorator()
            
    #         @DATA
    #         @dataclass
    #         class NodeWithDict:
    #             name: str
    #             refs: Dict[str, 'NodeWithDict']
            
    #         storage = self.create_storage(DATA, engine_type)
    #         node1 = NodeWithDict("node1", {})
    #         node2 = NodeWithDict("node2", {})
    #         node1.refs["other"] = node2
    #         node2.refs["other"] = node1
            
    #         storage.merge(node1)
    #         queried = storage.query(NodeWithDict).filter_by_id(node1.get_primary_key())
    #         return node1, queried
        
    #     for engine_type in range(2):
    #         original, queried = setup_and_query(engine_type)
    #         self.assertEqual(original, queried)

    def tearDown(self):
        if os.path.exists("test_equality.json"):
            os.remove("test_equality.json")

if __name__ == '__main__':
    unittest.main()