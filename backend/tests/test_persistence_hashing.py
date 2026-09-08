import unittest
import os
import sqlite3
from core.equation_ast import (
    SymbolNode, NumberNode, BinaryOpNode, EquationAST, EquationDocument,
    SymbolDefinition, ProvenanceRecord
)
from core.persistence import EquationPersistence

class TestHashingAndPersistence(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_persistence.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = EquationPersistence(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_semantic_hash_stability(self):
        # x + y == y + x
        a1 = EquationAST(lhs=SymbolNode("z"), rhs=BinaryOpNode("+", SymbolNode("x"), SymbolNode("y")))
        a2 = EquationAST(lhs=SymbolNode("z"), rhs=BinaryOpNode("+", SymbolNode("y"), SymbolNode("x")))

        self.assertEqual(a1.semantic_hash(), a2.semantic_hash())

        # x * y == y * x
        m1 = EquationAST(lhs=SymbolNode("z"), rhs=BinaryOpNode("*", SymbolNode("x"), SymbolNode("y")))
        m2 = EquationAST(lhs=SymbolNode("z"), rhs=BinaryOpNode("*", SymbolNode("y"), SymbolNode("x")))

        self.assertEqual(m1.semantic_hash(), m2.semantic_hash())

        # Subtraction is not commutative
        s1 = EquationAST(lhs=SymbolNode("z"), rhs=BinaryOpNode("-", SymbolNode("x"), SymbolNode("y")))
        s2 = EquationAST(lhs=SymbolNode("z"), rhs=BinaryOpNode("-", SymbolNode("y"), SymbolNode("x")))

        self.assertNotEqual(s1.semantic_hash(), s2.semantic_hash())

    def test_persistence_lineage(self):
        # Create initial version
        a1 = EquationAST(lhs=SymbolNode("z"), rhs=BinaryOpNode("+", SymbolNode("x"), SymbolNode("y")))
        doc1 = EquationDocument(
            id="EQ-001", version="v1.0", ast=a1, symbols={},
            provenance=ProvenanceRecord(author="Agent", transformation="Init")
        )
        self.db.save_version(doc1)

        # Verify it's saved
        history = self.db.get_version_history("EQ-001")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['version_label'], "v1.0")
        self.assertIsNone(history[0]['parent_hash_id'])

        # Mutate to create a new version
        h1 = doc1.semantic_hash
        a1.rhs.op = "-"
        doc1.version = "v1.1"
        self.db.save_version(doc1, parent_hash=h1)

        history = self.db.get_version_history("EQ-001")
        self.assertEqual(len(history), 2)

        self.assertEqual(history[0]['hash_id'], h1)
        self.assertEqual(history[1]['parent_hash_id'], h1)
        self.assertNotEqual(history[0]['hash_id'], history[1]['hash_id'])

if __name__ == '__main__':
    unittest.main()
