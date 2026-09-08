from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/api/equation/fixture")
def get_fixture():
    doc = get_quadratic_drag_fixture()
    validation = doc.validate()

    # In a real system, the telemetry warnings might be merged from various subsystems
    # Here we simulate the pipeline also performing a MathML conversion
    conversion_res = doc.convert("Content MathML")
    if conversion_res.warnings:
        validation.warnings.extend(conversion_res.warnings)

    return {
        "equation": doc,
        "validation": validation
    }
