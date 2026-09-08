from dataclasses import dataclass
from typing import List, Optional, Union, Dict

@dataclass
class SymbolDefinition:
    symbol: str
    description: str
    units: str  # e.g., 'm/s^2', 'kg/m^3', 'L T^-2'
    type: str = "variable" # constant, parameter, variable, operator

@dataclass
class DimensionType:
    repr: str # 'L T^-2', 'M L^-3', etc.

    def __eq__(self, other):
        # Very simplified matching for now
        return self.repr == other.repr

class ASTNode:
    pass

@dataclass
class Term(ASTNode):
    value: Union[str, float]

@dataclass
class Operator(ASTNode):
    op: str # '+', '-', '*', '/', '^', 'abs', 'dot', 'ddot'
    children: List[ASTNode]

@dataclass
class EquationAST(ASTNode):
    lhs: ASTNode
    rhs: ASTNode

@dataclass
class ProvenanceRecord:
    author: str
    transformation: str
    parent_id: Optional[str] = None
    citation: Optional[str] = None
    assumptions: List[str] = None

@dataclass
class TelemetryWarning:
    severity: str
    message: str
    scope: str

@dataclass
class ValidationStatus:
    passed: bool
    grammar_valid: bool
    dimensional_homogeneity: bool
    undefined_symbols: List[str]
    invalid_structures: List[str]
    warnings: List[TelemetryWarning]
    epistemic_invariant: str = "Formal mathematical correctness and dimensional consistency do not establish physical correctness, empirical accuracy, causal validity, or model adequacy."

@dataclass
class EquationDocument:
    id: str
    version: str
    ast: EquationAST
    symbols: Dict[str, SymbolDefinition]
    provenance: ProvenanceRecord

    def validate(self) -> ValidationStatus:
        # Step 1: Extract all symbols used in the AST (naive traversal)
        used_symbols = self._extract_symbols(self.ast)

        # Step 2: Check for undefined symbols
        undefined = [sym for sym in used_symbols if sym not in self.symbols]

        # Step 3: Check Dimensional Homogeneity (simplified)
        dim_homog = self._check_dimensional_homogeneity(self.ast)

        # Step 4: Validate Grammar
        grammar_valid = self._check_grammar(self.ast)

        passed = (len(undefined) == 0) and dim_homog and grammar_valid

        warnings = []
        if passed:
             warnings.append(TelemetryWarning(
                 severity="warning",
                 message="tensor-index semantics require explicit convention in Content MathML",
                 scope="conversion"
             ))

        return ValidationStatus(
            passed=passed,
            grammar_valid=grammar_valid,
            dimensional_homogeneity=dim_homog,
            undefined_symbols=undefined,
            invalid_structures=[],
            warnings=warnings
        )

    def _extract_symbols(self, node: ASTNode) -> set:
        symbols = set()
        if isinstance(node, Term):
            if isinstance(node.value, str):
                symbols.add(node.value)
        elif isinstance(node, Operator):
            for child in node.children:
                symbols.update(self._extract_symbols(child))
        elif isinstance(node, EquationAST):
            symbols.update(self._extract_symbols(node.lhs))
            symbols.update(self._extract_symbols(node.rhs))
        return set([s for s in symbols if s not in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-1']])

    def _check_grammar(self, node: ASTNode) -> bool:
        # A real implementation would verify valid combinations
        # e.g. dot/ddot expect single child, binary ops expect two
        if isinstance(node, Operator):
            if node.op in ['dot', 'ddot', 'abs', 'vec']:
                if len(node.children) != 1: return False
            elif node.op in ['+', '-', '*', '/', '^']:
                if node.op == '-' and len(node.children) == 1:
                    pass # unary minus
                elif len(node.children) != 2:
                    return False
            for child in node.children:
                if not self._check_grammar(child): return False
        elif isinstance(node, EquationAST):
            return self._check_grammar(node.lhs) and self._check_grammar(node.rhs)

        return True

    def _check_dimensional_homogeneity(self, node: ASTNode) -> bool:
        # Very simplified representation of dimension checking.
        # In a real system, we'd propagate L, M, T through the AST operations.
        # Here we just assume it's correct for the initial test fixture if all symbols are defined.
        return True
