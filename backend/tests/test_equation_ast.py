import unittest
from core.equation_ast import (
    EquationDocument, EquationAST, BinaryOpNode, UnaryOpNode,
    DerivativeNode, SymbolNode, NumberNode, FunctionNode,
    SymbolDefinition, ProvenanceRecord
)

class TestEquationValidation(unittest.TestCase):
    def setUp(self):
        # We will use the fixture setup directly
        from core.fastapi_app import get_quadratic_drag_fixture
        self.doc = get_quadratic_drag_fixture()

    def test_valid_equation(self):
        # This is a valid dimensional equation
        status = self.doc.validate()
        self.assertTrue(status.passed)
        self.assertTrue(status.grammar_valid)
        self.assertTrue(status.dimensional_homogeneity)
        self.assertEqual(len(status.undefined_symbols), 0)
        self.assertEqual(len(status.invalid_structures), 0)
        self.assertEqual(len(status.dimension_diagnostics), 0)

    def test_dimensionally_invalid_equation(self):
        # Change LHS to be velocity instead of acceleration
        # v = -g*j - ...
        # LHS is [L T^-1], RHS is [L T^-2]
        self.doc.ast.lhs.order = 1
        status = self.doc.validate()
        self.assertFalse(status.passed)
        self.assertFalse(status.dimensional_homogeneity)
        self.assertGreater(len(status.dimension_diagnostics), 0)
        self.assertIn("Equation mismatch", status.dimension_diagnostics[0])

    def test_derivative_dimension_propagation(self):
        # Just check that derivative of position (L) wrt time (T) order 2 is L T^-2
        # We can test this by substituting LHS into RHS and checking if it's homogeneous
        # e.g., r = r_ddot (invalid)
        ast = EquationAST(lhs=SymbolNode('r'), rhs=DerivativeNode(SymbolNode('r'), 2))
        self.doc.ast = ast
        status = self.doc.validate()
        self.assertFalse(status.passed)
        self.assertIn("Equation mismatch", status.dimension_diagnostics[0])

    def test_multiplication_division_propagation(self):
        # F = m*a
        # Change unit format slightly so regex parser catches it correctly 'kg m / s^2' -> 'kg*m/s^2'
        symbols = {
            'F': SymbolDefinition('F', '', 'M L/T^2'),
            'm': SymbolDefinition('m', '', 'M'),
            'a': SymbolDefinition('a', '', 'L/T^2'),
        }
        ast = EquationAST(lhs=SymbolNode('F'), rhs=BinaryOpNode('*', SymbolNode('m'), SymbolNode('a')))
        doc = EquationDocument("test", "v1", ast, symbols, ProvenanceRecord("", ""))
        status = doc.validate()
        self.assertTrue(status.passed)

        # F = m/a (Invalid)
        ast2 = EquationAST(lhs=SymbolNode('F'), rhs=BinaryOpNode('/', SymbolNode('m'), SymbolNode('a')))
        doc2 = EquationDocument("test", "v1", ast2, symbols, ProvenanceRecord("", ""))
        status2 = doc2.validate()
        self.assertFalse(status2.passed)
        self.assertIn("Equation mismatch", status2.dimension_diagnostics[0])

    def test_addition_subtraction_mismatch(self):
        # m + a (M + L/T^2) -> Should fail
        symbols = {
            'F': SymbolDefinition('F', '', 'M L/T^2'),
            'm': SymbolDefinition('m', '', 'M'),
            'a': SymbolDefinition('a', '', 'L/T^2'),
        }
        ast = EquationAST(lhs=SymbolNode('F'), rhs=BinaryOpNode('+', SymbolNode('m'), SymbolNode('a')))
        doc = EquationDocument("test", "v1", ast, symbols, ProvenanceRecord("", ""))
        status = doc.validate()
        self.assertFalse(status.passed)
        self.assertFalse(status.dimensional_homogeneity)
        self.assertTrue(any("Dimension mismatch in +" in d for d in status.dimension_diagnostics))

    def test_unsupported_operator(self):
        ast = EquationAST(lhs=SymbolNode('r'), rhs=BinaryOpNode('%', SymbolNode('r'), NumberNode(2)))
        self.doc.ast = ast
        status = self.doc.validate()
        self.assertFalse(status.passed)
        self.assertFalse(status.grammar_valid)
        self.assertTrue(any("Unsupported binary operator: %" in d for d in status.invalid_structures))

    def test_invalid_arity(self):
        # Unary missing child
        ast = EquationAST(lhs=SymbolNode('r'), rhs=UnaryOpNode('-', None))
        self.doc.ast = ast
        status = self.doc.validate()
        self.assertFalse(status.passed)
        self.assertFalse(status.grammar_valid)
        self.assertTrue(any("missing child" in d for d in status.invalid_structures))

    def test_conversion_warning_behavior(self):
        # Validate should have 0 warnings initially
        status = self.doc.validate()
        self.assertEqual(len(status.warnings), 0)

        # Calling convert should return warnings
        conv = self.doc.convert("Content MathML")
        self.assertEqual(len(conv.warnings), 1)
        self.assertEqual(conv.warnings[0].scope, "conversion")

    def test_epistemic_invariant(self):
        status = self.doc.validate()
        self.assertIn("Formal mathematical correctness", status.epistemic_invariant)

if __name__ == '__main__':
    unittest.main()
