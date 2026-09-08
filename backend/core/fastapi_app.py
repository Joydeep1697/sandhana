from core.latex_exporter import LatexExporter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from typing import Optional
class EditRequest(BaseModel):
    target_node_path: str # e.g. "rhs.term1.op"
    new_value: str

from core.equation_ast import (
    EquationDocument, EquationAST, BinaryOpNode, UnaryOpNode,
    DerivativeNode, SymbolNode, NumberNode,
    SymbolDefinition, ProvenanceRecord
)

app = FastAPI(title="SANDHANA Mathematical Equation & Derivation Workbench")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_quadratic_drag_fixture():
    # r¨ = -g j-hat - (rho0 Cd A / 2m) |r-dot| r-dot

    # term1: -g * j-hat
    g_sym = SymbolNode('g')
    j_sym = SymbolNode('j_hat')
    neg_g = UnaryOpNode('-', g_sym)
    term1 = BinaryOpNode('*', neg_g, j_sym)

    # term2: (rho0 * Cd * A / (2*m)) * abs(r-dot) * r-dot
    rho0_sym = SymbolNode('rho0')
    Cd_sym = SymbolNode('Cd')
    A_sym = SymbolNode('A')
    two = NumberNode(2.0)
    m_sym = SymbolNode('m')

    rho_cd = BinaryOpNode('*', rho0_sym, Cd_sym)
    num = BinaryOpNode('*', rho_cd, A_sym)
    den = BinaryOpNode('*', two, m_sym)
    coef = BinaryOpNode('/', num, den)

    r_sym = SymbolNode('r')
    r_dot = DerivativeNode(child=r_sym, order=1, with_respect_to='t')
    abs_r_dot = UnaryOpNode('abs', r_dot)

    vel_term = BinaryOpNode('*', abs_r_dot, r_dot)
    term2 = BinaryOpNode('*', coef, vel_term)

    rhs = BinaryOpNode('-', term1, term2)
    lhs = DerivativeNode(child=r_sym, order=2, with_respect_to='t')

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
        transformation="Reduced-order quadratic-drag model",
        parent_id="#EQ-098-B1",
        citation="Navier (1822), Stokes (1845)",
        assumptions=["Incompressible", "Constant density"]
    )

    return EquationDocument(
        id="#EQ-098-B2",
        version="v2.4",
        ast=ast,
        symbols=symbols,
        provenance=prov
    )


# Global state just for this interactive slice
current_doc = get_quadratic_drag_fixture()

@app.get("/api/equation/fixture")
def get_fixture():
    validation = current_doc.validate()

    conversion_res = current_doc.convert("Content MathML")
    if conversion_res.warnings:
        validation.warnings.extend(conversion_res.warnings)

    latex = LatexExporter.export(current_doc.ast)

    return {
        "equation": current_doc,
        "validation": validation,
        "latex": latex
    }

@app.post("/api/equation/edit")
def edit_equation(req: EditRequest):
    global current_doc
    # Super simple AST patching for the vertical slice
    # Supported edits for demo:
    # - Change 'm' to 'M' (invalidates dimension unless M is defined, wait M is a dimension! Let's just break it with 'invalid_sym')
    # - Change RHS operator from '-' to '+'

    if req.target_node_path == "rhs.op":
        current_doc.ast.rhs.op = req.new_value
    elif req.target_node_path == "rhs.right.left.right.right.name":
        # This points to 'm' in denominator
        current_doc.ast.rhs.right.left.right.right.name = req.new_value
    elif req.target_node_path == "rhs.right.right.right.child.name":
         # Change r to v in velocity term
         current_doc.ast.rhs.right.right.right.child.name = req.new_value

    validation = current_doc.validate()
    latex = LatexExporter.export(current_doc.ast)
    return {
        "equation": current_doc,
        "validation": validation,
        "latex": latex
    }
