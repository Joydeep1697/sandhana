import unittest
from core.equation_ast import (
    EquationDocument, EquationAST, Operator, Term,
    SymbolDefinition, ProvenanceRecord
)

class TestEquationValidation(unittest.TestCase):
    def setUp(self):
        # r¨ = -g j-hat - (rho0 Cd A / 2m) |r-dot| r-dot
        # Let's build the AST for the RHS
        # term1: -g * j-hat
        term1 = Operator('*', [Operator('-', [Term('g')]), Term('j_hat')])

        # term2: (rho0 * Cd * A / 2m) * abs(r-dot) * r-dot
        coef_numerator = Operator('*', [Operator('*', [Term('rho0'), Term('Cd')]), Term('A')])
        coef_denom = Operator('*', [Term('2'), Term('m')])
        coef = Operator('/', [coef_numerator, coef_denom])

        rdot = Operator('dot', [Term('r')])
        abs_rdot = Operator('abs', [rdot])

        term2 = Operator('*', [Operator('*', [coef, abs_rdot]), rdot])

        rhs = Operator('-', [term1, term2])
        lhs = Operator('ddot', [Term('r')])

        ast = EquationAST(lhs=lhs, rhs=rhs)

        symbols = {
            'r': SymbolDefinition('r', 'Position vector', 'm', 'variable'),
            'g': SymbolDefinition('g', 'Acceleration due to gravity', 'm/s^2', 'constant'),
            'j_hat': SymbolDefinition('j_hat', 'Vertical unit vector', '1', 'constant'),
            'rho0': SymbolDefinition('rho0', 'Reference fluid density', 'kg/m^3', 'parameter'),
            'Cd': SymbolDefinition('Cd', 'Drag coefficient', '1', 'parameter'),
            'A': SymbolDefinition('A', 'Cross-sectional area', 'm^2', 'parameter'),
            'm': SymbolDefinition('m', 'Projectile mass', 'kg', 'parameter'),
        }

        prov = ProvenanceRecord(
            author="Model Builder Agent",
            transformation="Symbolic boundary-layer drag projection",
            parent_id="#EQ-098-B1",
            citation="Navier (1822), Stokes (1845)",
            assumptions=["Incompressible", "Constant density"]
        )

        self.doc = EquationDocument(
            id="#EQ-098-B2",
            version="v2.4",
            ast=ast,
            symbols=symbols,
            provenance=prov
        )

    def test_valid_equation(self):
        status = self.doc.validate()
        self.assertTrue(status.passed)
        self.assertTrue(status.grammar_valid)
        self.assertTrue(status.dimensional_homogeneity)
        self.assertEqual(len(status.undefined_symbols), 0)
        self.assertIn("tensor-index semantics", status.warnings[0].message)
        self.assertIn("Formal mathematical correctness", status.epistemic_invariant)

    def test_undefined_symbol(self):
        # Remove 'm' from definitions
        del self.doc.symbols['m']
        status = self.doc.validate()
        self.assertFalse(status.passed)
        self.assertIn('m', status.undefined_symbols)

    def test_invalid_grammar(self):
        # Add an invalid operator structure: a binary operator with 3 children
        self.doc.ast.rhs.children.append(Term('extra'))
        status = self.doc.validate()
        self.assertFalse(status.passed)
        self.assertFalse(status.grammar_valid)

if __name__ == '__main__':
    unittest.main()
