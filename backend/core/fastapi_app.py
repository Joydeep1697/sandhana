
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.equation_ast import (
    EquationDocument, EquationAST, Operator, Term,
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
    # term1: -g * j-hat
    term1 = Operator('-', [Operator('*', [Term('g'), Term('j_hat')])])

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
    return {
        "equation": doc,
        "validation": validation
    }
