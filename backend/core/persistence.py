import sqlite3
import json
from typing import List, Optional, Dict
from core.equation_ast import (
    EquationDocument, EquationAST, SymbolDefinition,
    ProvenanceRecord, ValidationStatus, TelemetryWarning
)

class EquationPersistence:
    def __init__(self, db_path: str = "sandhana_equations.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Equation Lineage / Versioning
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS equation_versions (
                    hash_id TEXT PRIMARY KEY,
                    equation_id TEXT NOT NULL,
                    version_label TEXT NOT NULL,
                    parent_hash_id TEXT,
                    ast_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Metadata
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS provenance_records (
                    hash_id TEXT PRIMARY KEY,
                    author TEXT,
                    transformation TEXT,
                    citation TEXT,
                    assumptions TEXT,
                    FOREIGN KEY(hash_id) REFERENCES equation_versions(hash_id)
                )
            ''')

            # Validation state
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS validation_states (
                    hash_id TEXT PRIMARY KEY,
                    passed BOOLEAN,
                    grammar_valid BOOLEAN,
                    dimensional_homogeneity BOOLEAN,
                    diagnostics TEXT,
                    epistemic_invariant TEXT,
                    FOREIGN KEY(hash_id) REFERENCES equation_versions(hash_id)
                )
            ''')

            # Symbol definitions for this version
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS symbol_definitions (
                    hash_id TEXT,
                    symbol TEXT,
                    description TEXT,
                    units TEXT,
                    type TEXT,
                    PRIMARY KEY (hash_id, symbol),
                    FOREIGN KEY(hash_id) REFERENCES equation_versions(hash_id)
                )
            ''')

            conn.commit()

    def save_version(self, doc: EquationDocument, parent_hash: Optional[str] = None):
        hash_id = doc.semantic_hash

        # In a real app we'd serialize the AST properly.
        # Here we mock serialization by storing canonical_repr as ast_json just to satisfy persistence schema requirements,
        # but in a production vertical slice we'd write a true JSON encoder/decoder for ASTNode.
        ast_json = doc.ast._canonical_repr()

        validation = doc.validate()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Save version
            cursor.execute('''
                INSERT OR IGNORE INTO equation_versions (hash_id, equation_id, version_label, parent_hash_id, ast_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (hash_id, doc.id, doc.version, parent_hash, ast_json))

            # Save provenance
            assumptions_json = json.dumps(doc.provenance.assumptions)
            cursor.execute('''
                INSERT OR IGNORE INTO provenance_records (hash_id, author, transformation, citation, assumptions)
                VALUES (?, ?, ?, ?, ?)
            ''', (hash_id, doc.provenance.author, doc.provenance.transformation, doc.provenance.citation, assumptions_json))

            # Save validation
            diagnostics_json = json.dumps({
                "undefined_symbols": validation.undefined_symbols,
                "invalid_structures": validation.invalid_structures,
                "dimension_diagnostics": validation.dimension_diagnostics
            })
            cursor.execute('''
                INSERT OR IGNORE INTO validation_states (hash_id, passed, grammar_valid, dimensional_homogeneity, diagnostics, epistemic_invariant)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (hash_id, validation.passed, validation.grammar_valid, validation.dimensional_homogeneity, diagnostics_json, validation.epistemic_invariant))

            # Save symbols
            for sym_name, sym_def in doc.symbols.items():
                cursor.execute('''
                    INSERT OR IGNORE INTO symbol_definitions (hash_id, symbol, description, units, type)
                    VALUES (?, ?, ?, ?, ?)
                ''', (hash_id, sym_def.symbol, sym_def.description, sym_def.units, sym_def.type))

            conn.commit()

    def get_version_history(self, equation_id: str) -> List[Dict]:
        """Returns the lineage of an equation ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT hash_id, version_label, parent_hash_id, created_at
                FROM equation_versions
                WHERE equation_id = ?
                ORDER BY created_at ASC
            ''', (equation_id,))

            return [dict(row) for row in cursor.fetchall()]
