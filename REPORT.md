# Verification Report

1. **Persistence Tables & Models**:
   - `equation_versions`: Stores the canonical AST JSON representation, version label, and parent hash ID. Primary key is the AST's `hash_id`.
   - `symbol_definitions`: Stores variables, parameters, constants, and their exact SI units for each `hash_id`.
   - `validation_states`: Stores dimensions, grammar diagnostics, the epistemic invariant context string, the `validator_version`, and a `created_at` timestamp, tied directly to the equation `hash_id`.
   - `provenance_records`: Stores the author, citation, assumption list, and descriptive transformation name per `hash_id`.

2. **API Endpoints**:
   - `GET /api/equation/fixture`: Instantiates the in-memory SQLite DB, loads the quadratic-drag AST, hashes it, saves the new lineage, executes validation, and returns the full JSON representation + LaTeX.
   - `POST /api/equation/edit`: Parses targeted JSON mutation operations against the semantic AST. It calculates the semantic hash before and after the mutation; if the hash changed, the old hash is explicitly linked as the `parent_hash_id` in the `equation_versions` table and updated in the active `current_doc.provenance.parent_id`.
   - `GET /api/equation/provenance_history`: Exposed to explicitly retrieve a lineage of historical provenance records joined across the `equation_versions` timeline.

3. **Semantic Hashing**:
   - Algorithm uses SHA-256 (`hashlib.sha256().hexdigest()`).
   - The hash digests a concatenated string comprising three inputs:
     - `ast._canonical_repr()`: A deterministic recursive representation of the math tree. Importantly, commutative operations (like `+`, `*`, and `=` sides) are sorted alphanumerically before hashing. E.g., `x + y` and `y + x` produce the same canonical string.
     - `symbols`: The symbol dictionary is sorted and serialized (`symbol:units:type`).
     - `assumptions`: The array of assumptions is alphabetically sorted.

4. **Avoiding Duplicate Versions**:
   - Because commutative nodes are sorted internally by the `semantic_hash`, two identical mathematical ASTs (even if typed differently like `x*y` vs `y*x`) will generate the exact same `hash_id`. The persistence layer (`backend/core/persistence.py`) uses `INSERT OR IGNORE` which silently rejects duplicates with the same primary key (`hash_id`), meaning no superfluous versions are created.

5. **Parent-Version Linkage**:
   - In `fastapi_app.py:edit_equation`, the pre-mutation hash is saved as `old_hash`. After the AST edit occurs, if the new hash does not equal `old_hash`, it creates a new database record, sets the runtime `current_doc.provenance.parent_id = old_hash`, and inserts `old_hash` into the `parent_hash_id` column.

6. **Validation Constraints**:
   - `validation_states` defines a foreign key tightly binding the test results exclusively to a unique `hash_id`. The schema includes `validator_version` to track when new dimension engines might change previous verdicts, and a `created_at` timestamp.

7. **Provenance Immutability**:
   - `provenance_records` uses `INSERT OR IGNORE` alongside the cryptographic `hash_id` as the primary key. Once an AST is saved, its historical provenance assumptions cannot be silently mutated using SQLite updates.

8. **Database Commitment**:
   - `sandhana_equations.db` was removed from git cache using `git rm --cached` and excluded via `.gitignore`.

9. **Test Results**:
   - **Command:** `PYTHONPATH=$(pwd)/backend python3 -m unittest discover backend/tests`
   - **Unit & Persistence:** `test_equation_ast.py` and `test_persistence_hashing.py` successfully verify commutative hash stability, dimension checking, derivative propagation, and lineage tracking.
   - **Frontend Integration:** `test_frontend_integration.py` successfully verifies the HTML screens possess the required LaTeX DOM elements and JavaScript update hooks.
   - **End-to-End Editor:** `test_e2e_editor.py` spins up `uvicorn` and `http.server`, uses `Playwright` to load Chromium, executes visual edits, and verifies DOM changes natively.
   - **Exact Output:** 15 tests ran successfully, 0 failures, 0 errors.

10. **Stubs & Limitations**:
    - `Content MathML` is clearly stubbed in `backend/core/equation_ast.py` returning `<mathml-stub>`. Numerical solvers are completely un-implemented as required.
    - Limitation: The semantic hashing canonicalizer is structurally naive. It only sorts commutative terms superficially. Deep associative simplifications (e.g., `(x+y)+z == x+(y+z)`) or trigonometric identities are not resolved to the same hash.
