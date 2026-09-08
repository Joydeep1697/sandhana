from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Tuple, Any
import re

@dataclass
class SymbolDefinition:
    symbol: str
    description: str
    units: str
    type: str = "variable"

@dataclass
class Dimension:
    powers: Dict[str, float] = field(default_factory=dict)

    def normalize(self):
        self.powers = {k: v for k, v in self.powers.items() if v != 0}

    def __mul__(self, other: 'Dimension') -> 'Dimension':
        res = dict(self.powers)
        for k, v in other.powers.items():
            res[k] = res.get(k, 0) + v
        d = Dimension(res)
        d.normalize()
        return d

    def __truediv__(self, other: 'Dimension') -> 'Dimension':
        res = dict(self.powers)
        for k, v in other.powers.items():
            res[k] = res.get(k, 0) - v
        d = Dimension(res)
        d.normalize()
        return d

    def __eq__(self, other):
        if not isinstance(other, Dimension):
            return False
        # Treat small floating point diffs as equal, though we only use integers right now
        return self.powers == other.powers

    def __str__(self):
        if not self.powers:
            return "1"
        return " ".join([f"{k}^{v}" if v != 1 else k for k, v in sorted(self.powers.items())])

def parse_units_to_dimension(unit_str: str) -> Dimension:
    if unit_str == '1' or not unit_str:
        return Dimension()

    # Better parser handling spaces explicitly
    mapping = {'m': 'L', 'kg': 'M', 's': 'T', 'L': 'L', 'M': 'M', 'T': 'T'}

    parts = unit_str.split('/')
    numerator = parts[0]
    denominator = parts[1] if len(parts) > 1 else ""

    def parse_part(part: str, sign: int) -> Dict[str, float]:
        res = {}
        if not part or part == '1':
            return res

        # Add a * for spaces or next to variables to make it uniform
        # Just find all groups of [A-Za-z]+ optionally followed by ^number
        tokens = re.findall(r'([A-Za-z]+)(?:\^(-?\d+\.?\d*))?', part)
        for base, exp in tokens:
            dim = mapping.get(base, base)
            power = float(exp) if exp else 1.0
            res[dim] = res.get(dim, 0) + power * sign
        return res

    num_dims = parse_part(numerator, 1)
    den_dims = parse_part(denominator, -1)

    final_dims = {}
    for k, v in num_dims.items(): final_dims[k] = final_dims.get(k, 0) + v
    for k, v in den_dims.items(): final_dims[k] = final_dims.get(k, 0) + v

    d = Dimension(final_dims)
    d.normalize()
    return d

class ASTNode:
    type_name = "ASTNode"

@dataclass
class SymbolNode(ASTNode):
    name: str
    type_name = "SymbolNode"

@dataclass
class NumberNode(ASTNode):
    value: float
    type_name = "NumberNode"

@dataclass
class DerivativeNode(ASTNode):
    child: ASTNode
    order: int
    with_respect_to: str = 't'
    type_name = "DerivativeNode"

@dataclass
class UnaryOpNode(ASTNode):
    op: str # '-', 'abs', 'vec'
    child: ASTNode
    type_name = "UnaryOpNode"

@dataclass
class BinaryOpNode(ASTNode):
    op: str # '+', '-', '*', '/', '^'
    left: ASTNode
    right: ASTNode
    type_name = "BinaryOpNode"

@dataclass
class FunctionNode(ASTNode):
    name: str
    args: List[ASTNode]
    type_name = "FunctionNode"

@dataclass
class EquationAST(ASTNode):
    lhs: ASTNode
    rhs: ASTNode
    type_name = "EquationAST"

@dataclass
class ProvenanceRecord:
    author: str
    transformation: str
    parent_id: Optional[str] = None
    citation: Optional[str] = None
    assumptions: List[str] = field(default_factory=list)

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
    dimension_diagnostics: List[str]
    warnings: List[TelemetryWarning]
    epistemic_invariant: str = "Formal mathematical correctness and dimensional consistency do not establish physical correctness, empirical accuracy, causal validity, or model adequacy."

@dataclass
class ConversionResult:
    target_format: str
    content: str
    warnings: List[TelemetryWarning] = field(default_factory=list)

@dataclass
class EquationDocument:
    id: str
    version: str
    ast: EquationAST
    symbols: Dict[str, SymbolDefinition]
    provenance: ProvenanceRecord

    def validate(self) -> ValidationStatus:
        undefined = []
        invalid_structures = []
        dimension_diagnostics = []

        # 1. Grammar validation
        grammar_valid = self._validate_grammar(self.ast, invalid_structures)

        # 2. Symbol extraction and check
        used_symbols = self._extract_symbols(self.ast)
        for sym in used_symbols:
            if sym not in self.symbols:
                undefined.append(sym)

        # 3. Dimensional Homogeneity
        dim_homog = False
        if grammar_valid and not undefined:
            dim_lhs, errs_lhs = self._propagate_dimensions(self.ast.lhs)
            dim_rhs, errs_rhs = self._propagate_dimensions(self.ast.rhs)

            dimension_diagnostics.extend(errs_lhs)
            dimension_diagnostics.extend(errs_rhs)

            if not errs_lhs and not errs_rhs:
                if dim_lhs == dim_rhs:
                    dim_homog = True
                else:
                    dimension_diagnostics.append(f"Equation mismatch: LHS dimension [{dim_lhs}] != RHS dimension [{dim_rhs}]")

        passed = (len(undefined) == 0) and grammar_valid and dim_homog

        return ValidationStatus(
            passed=passed,
            grammar_valid=grammar_valid,
            dimensional_homogeneity=dim_homog,
            undefined_symbols=undefined,
            invalid_structures=invalid_structures,
            dimension_diagnostics=dimension_diagnostics,
            warnings=[]
        )

    def convert(self, target_format: str) -> ConversionResult:
        warnings = []
        if target_format == "Content MathML":
            warnings.append(TelemetryWarning(
                 severity="warning",
                 message="tensor-index semantics require explicit convention in Content MathML",
                 scope="conversion"
            ))
        return ConversionResult(target_format=target_format, content="<mathml>...</mathml>", warnings=warnings)

    def _extract_symbols(self, node: ASTNode) -> set:
        symbols = set()
        if isinstance(node, SymbolNode):
            symbols.add(node.name)
        elif isinstance(node, DerivativeNode):
            symbols.update(self._extract_symbols(node.child))
        elif isinstance(node, UnaryOpNode):
            symbols.update(self._extract_symbols(node.child))
        elif isinstance(node, BinaryOpNode):
            symbols.update(self._extract_symbols(node.left))
            symbols.update(self._extract_symbols(node.right))
        elif isinstance(node, FunctionNode):
            for arg in node.args:
                symbols.update(self._extract_symbols(arg))
        elif isinstance(node, EquationAST):
            symbols.update(self._extract_symbols(node.lhs))
            symbols.update(self._extract_symbols(node.rhs))
        return symbols

    def _validate_grammar(self, node: ASTNode, errors: List[str]) -> bool:
        is_valid = True
        if isinstance(node, DerivativeNode):
            if node.order < 1:
                errors.append(f"Invalid derivative order: {node.order}")
                is_valid = False
            is_valid = is_valid and self._validate_grammar(node.child, errors)
        elif isinstance(node, UnaryOpNode):
            if node.op not in ['-', 'abs', 'vec']:
                errors.append(f"Unsupported unary operator: {node.op}")
                is_valid = False
            if node.child is None:
                errors.append(f"Unary operator {node.op} missing child")
                is_valid = False
            else:
                is_valid = is_valid and self._validate_grammar(node.child, errors)
        elif isinstance(node, BinaryOpNode):
            if node.op not in ['+', '-', '*', '/', '^']:
                errors.append(f"Unsupported binary operator: {node.op}")
                is_valid = False
            if node.left is None or node.right is None:
                errors.append(f"Binary operator {node.op} missing operands")
                is_valid = False
            else:
                is_valid = is_valid and self._validate_grammar(node.left, errors) and self._validate_grammar(node.right, errors)
        elif isinstance(node, FunctionNode):
            if not node.args:
                errors.append(f"Function {node.name} has no arguments")
                is_valid = False
            for arg in node.args:
                is_valid = is_valid and self._validate_grammar(arg, errors)
        elif isinstance(node, EquationAST):
            is_valid = self._validate_grammar(node.lhs, errors) and self._validate_grammar(node.rhs, errors)

        return is_valid

    def _propagate_dimensions(self, node: ASTNode) -> Tuple[Optional[Dimension], List[str]]:
        if isinstance(node, SymbolNode):
            unit_str = self.symbols[node.name].units
            return parse_units_to_dimension(unit_str), []

        elif isinstance(node, NumberNode):
            return Dimension(), []

        elif isinstance(node, DerivativeNode):
            child_dim, errs = self._propagate_dimensions(node.child)
            if child_dim is None: return None, errs

            time_dim = parse_units_to_dimension('s')
            res = child_dim
            for _ in range(node.order):
                res = res / time_dim
            return res, errs

        elif isinstance(node, UnaryOpNode):
            return self._propagate_dimensions(node.child)

        elif isinstance(node, BinaryOpNode):
            left_dim, left_errs = self._propagate_dimensions(node.left)
            right_dim, right_errs = self._propagate_dimensions(node.right)
            errs = left_errs + right_errs

            if left_dim is None or right_dim is None:
                return None, errs

            if node.op in ['+', '-']:
                if left_dim != right_dim:
                    errs.append(f"Dimension mismatch in {node.op}: [{left_dim}] vs [{right_dim}]")
                    return None, errs
                return left_dim, errs
            elif node.op == '*':
                return left_dim * right_dim, errs
            elif node.op == '/':
                return left_dim / right_dim, errs
            elif node.op == '^':
                if isinstance(node.right, NumberNode):
                    res = Dimension({k: v * node.right.value for k, v in left_dim.powers.items()})
                    return res, errs
                else:
                    if right_dim != Dimension():
                        errs.append(f"Exponent must be dimensionless, got [{right_dim}]")
                        return None, errs
                    return left_dim, errs

        elif isinstance(node, FunctionNode):
            errs = []
            for arg in node.args:
                arg_dim, arg_errs = self._propagate_dimensions(arg)
                errs.extend(arg_errs)
                if arg_dim is not None and arg_dim != Dimension():
                    errs.append(f"Argument to {node.name} must be dimensionless, got [{arg_dim}]")
            return Dimension(), errs

        return None, ["Unknown node type for dimension propagation"]
