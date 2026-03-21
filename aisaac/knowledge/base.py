"""
Knowledge Base Schema and Storage.

SQLite-backed structured storage for all extracted physics.
Every formula, prediction, parameter, and cross-theory claim
from every paper lives here with full provenance.
"""
from __future__ import annotations

import json
import sqlite3
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    year: int
    abstract: str
    theory_tags: list[str]          # which QG approaches this paper touches
    citation_count: int = 0
    is_review: bool = False
    tier: int = 1
    source_path: str = ""           # local path to PDF/LaTeX
    id: Optional[int] = None


@dataclass
class ExtractedFormula:
    paper_id: int
    latex: str                       # original LaTeX
    sympy_expr: str                  # sympy-parseable string (after normalization)
    formula_type: str                # prediction | key_equation | correction | mapping
    quantity_type: str               # spectral_dimension, newton_correction, etc.
    theory_slug: str                 # which QG approach
    description: str                 # natural language: what does this formula represent?
    variables: list[dict]            # [{symbol, meaning, dimensions}, ...]
    regime: str                      # where is this valid?
    approximations: str              # what approximations were made?
    normalized_latex: str = ""       # after notation normalization
    normalized_sympy: str = ""       # normalized sympy expression
    confidence: float = 0.0         # LLM confidence in extraction (0-1)
    id: Optional[int] = None

    def content_hash(self) -> str:
        """Hash for deduplication."""
        return hashlib.sha256(
            f"{self.theory_slug}:{self.quantity_type}:{self.latex}".encode()
        ).hexdigest()[:16]


@dataclass
class Prediction:
    """A specific numerical or symbolic prediction from a theory."""
    theory_slug: str
    quantity_type: str               # from QuantityType enum
    formula_id: int                  # FK to ExtractedFormula
    paper_id: int                    # FK to Paper
    symbolic_form: str               # sympy expression string
    numerical_value: Optional[float] = None  # if computable
    numerical_uncertainty: Optional[float] = None
    regime: str = ""
    notes: str = ""
    id: Optional[int] = None


@dataclass
class TheoryParameter:
    """A coupling constant or parameter specific to a theory."""
    theory_slug: str
    symbol: str
    meaning: str
    dimensions: str                  # e.g. "[L]^2" or "dimensionless"
    numerical_value: Optional[float] = None
    role: str = "coupling"           # coupling | observable | auxiliary
    id: Optional[int] = None


@dataclass
class ClaimedConnection:
    """An explicit claim in a paper that two theories are related."""
    paper_id: int
    theory_a: str
    theory_b: str
    connection_type: str             # agrees | disagrees | maps_to | generalizes
    formula_a_id: Optional[int] = None
    formula_b_id: Optional[int] = None
    description: str = ""
    id: Optional[int] = None


@dataclass
class Conjecture:
    """A machine-generated conjecture about cross-theory connections."""
    conjecture_type: str             # from ConjectureType enum
    title: str
    statement_latex: str             # precise mathematical statement
    statement_natural: str           # natural language description
    theories_involved: list[str]
    evidence_formula_ids: list[int]  # FKs to ExtractedFormula
    evidence_paper_ids: list[int]    # FKs to Paper
    # verification
    algebraic_verified: Optional[bool] = None
    numerical_verified: Optional[bool] = None
    dimensional_verified: Optional[bool] = None
    counterexample_found: Optional[bool] = None
    is_novel: Optional[bool] = None  # not found in literature
    # scoring
    evidence_score: float = 0.0
    significance_score: float = 0.0
    combined_score: float = 0.0
    status: str = "proposed"         # proposed | verified | disproved | known
    sympy_verified: bool = False     # True if conjecture was derived by executing sympy code
    notes: str = ""
    id: Optional[int] = None


# ── Database Manager ─────────────────────────────────────────────

class KnowledgeBase:
    """SQLite-backed knowledge base for all extracted physics."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS papers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        arxiv_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        authors TEXT NOT NULL,           -- JSON list
        year INTEGER,
        abstract TEXT,
        theory_tags TEXT NOT NULL,       -- JSON list
        citation_count INTEGER DEFAULT 0,
        is_review INTEGER DEFAULT 0,
        tier INTEGER DEFAULT 1,
        source_path TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS formulas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id INTEGER NOT NULL REFERENCES papers(id),
        latex TEXT NOT NULL,
        sympy_expr TEXT DEFAULT '',
        formula_type TEXT NOT NULL,
        quantity_type TEXT DEFAULT 'other',
        theory_slug TEXT NOT NULL,
        description TEXT DEFAULT '',
        variables TEXT DEFAULT '[]',     -- JSON
        regime TEXT DEFAULT '',
        approximations TEXT DEFAULT '',
        normalized_latex TEXT DEFAULT '',
        normalized_sympy TEXT DEFAULT '',
        confidence REAL DEFAULT 0.0,
        content_hash TEXT DEFAULT '',
        UNIQUE(content_hash)
    );

    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        theory_slug TEXT NOT NULL,
        quantity_type TEXT NOT NULL,
        formula_id INTEGER REFERENCES formulas(id),
        paper_id INTEGER NOT NULL REFERENCES papers(id),
        symbolic_form TEXT NOT NULL,
        numerical_value REAL,
        numerical_uncertainty REAL,
        regime TEXT DEFAULT '',
        notes TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS parameters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        theory_slug TEXT NOT NULL,
        symbol TEXT NOT NULL,
        meaning TEXT DEFAULT '',
        dimensions TEXT DEFAULT '',
        numerical_value REAL,
        role TEXT DEFAULT 'coupling'
    );

    CREATE TABLE IF NOT EXISTS claimed_connections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id INTEGER NOT NULL REFERENCES papers(id),
        theory_a TEXT NOT NULL,
        theory_b TEXT NOT NULL,
        connection_type TEXT NOT NULL,
        formula_a_id INTEGER REFERENCES formulas(id),
        formula_b_id INTEGER REFERENCES formulas(id),
        description TEXT DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS conjectures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conjecture_type TEXT NOT NULL,
        title TEXT NOT NULL,
        statement_latex TEXT NOT NULL,
        statement_natural TEXT NOT NULL,
        theories_involved TEXT NOT NULL, -- JSON list
        evidence_formula_ids TEXT NOT NULL, -- JSON list
        evidence_paper_ids TEXT NOT NULL,   -- JSON list
        algebraic_verified INTEGER,
        numerical_verified INTEGER,
        dimensional_verified INTEGER,
        counterexample_found INTEGER,
        is_novel INTEGER,
        evidence_score REAL DEFAULT 0.0,
        significance_score REAL DEFAULT 0.0,
        combined_score REAL DEFAULT 0.0,
        status TEXT DEFAULT 'proposed',
        notes TEXT DEFAULT ''
    );

    CREATE INDEX IF NOT EXISTS idx_formulas_theory ON formulas(theory_slug);
    CREATE INDEX IF NOT EXISTS idx_formulas_quantity ON formulas(quantity_type);
    CREATE INDEX IF NOT EXISTS idx_formulas_type ON formulas(formula_type);
    CREATE INDEX IF NOT EXISTS idx_predictions_quantity ON predictions(quantity_type);
    CREATE INDEX IF NOT EXISTS idx_predictions_theory ON predictions(theory_slug);
    CREATE INDEX IF NOT EXISTS idx_papers_theory ON papers(theory_tags);
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = __import__("threading").Lock()
        self.conn.executescript(self.SCHEMA)

    # ── Papers ───────────────────────────────────────────────────

    def insert_paper(self, p: Paper) -> int:
        with self._lock:
            cur = self.conn.execute(
                """INSERT OR IGNORE INTO papers
                   (arxiv_id, title, authors, year, abstract, theory_tags,
                    citation_count, is_review, tier, source_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (p.arxiv_id, p.title, json.dumps(p.authors), p.year, p.abstract,
                 json.dumps(p.theory_tags), p.citation_count, int(p.is_review),
                 p.tier, p.source_path),
            )
            self.conn.commit()
            if cur.lastrowid == 0:
                row = self.conn.execute(
                    "SELECT id FROM papers WHERE arxiv_id = ?", (p.arxiv_id,)
                ).fetchone()
                return row["id"]
            return cur.lastrowid

    def get_paper(self, arxiv_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        ).fetchone()
        return dict(row) if row else None

    def count_papers(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

    # ── Formulas ─────────────────────────────────────────────────

    def insert_formula(self, f: ExtractedFormula) -> int:
        chash = f.content_hash()
        with self._lock:
            cur = self.conn.execute(
                """INSERT OR IGNORE INTO formulas
                   (paper_id, latex, sympy_expr, formula_type, quantity_type,
                    theory_slug, description, variables, regime, approximations,
                    normalized_latex, normalized_sympy, confidence, content_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f.paper_id, f.latex, f.sympy_expr, f.formula_type,
                 f.quantity_type, f.theory_slug, f.description,
                 json.dumps(f.variables), f.regime, f.approximations,
                 f.normalized_latex, f.normalized_sympy, f.confidence, chash),
            )
            self.conn.commit()
            return cur.lastrowid

    def get_formulas_by_theory(self, theory_slug: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM formulas WHERE theory_slug = ?", (theory_slug,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_formulas_by_quantity(self, quantity_type: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM formulas WHERE quantity_type = ?", (quantity_type,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_predictions_for_quantity(self, quantity_type: str) -> list[dict]:
        """Get all predictions across all theories for a given quantity."""
        rows = self.conn.execute(
            """SELECT f.*, p.title as paper_title, p.arxiv_id
               FROM formulas f
               JOIN papers p ON f.paper_id = p.id
               WHERE f.quantity_type = ? AND f.formula_type IN ('prediction', 'correction')
               ORDER BY f.theory_slug""",
            (quantity_type,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_formulas(self, formula_types: list[str] | None = None) -> list[dict]:
        if formula_types:
            placeholders = ",".join("?" * len(formula_types))
            rows = self.conn.execute(
                f"SELECT * FROM formulas WHERE formula_type IN ({placeholders})",
                formula_types,
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM formulas").fetchall()
        return [dict(r) for r in rows]

    def count_formulas(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM formulas").fetchone()[0]

    # ── Predictions ──────────────────────────────────────────────

    def insert_prediction(self, pred: Prediction) -> int:
        cur = self.conn.execute(
            """INSERT INTO predictions 
               (theory_slug, quantity_type, formula_id, paper_id,
                symbolic_form, numerical_value, numerical_uncertainty, regime, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (pred.theory_slug, pred.quantity_type, pred.formula_id,
             pred.paper_id, pred.symbolic_form, pred.numerical_value,
             pred.numerical_uncertainty, pred.regime, pred.notes),
        )
        self.conn.commit()
        return cur.lastrowid

    # ── Claimed Connections ──────────────────────────────────────

    def insert_connection(self, conn_obj: ClaimedConnection) -> int:
        cur = self.conn.execute(
            """INSERT INTO claimed_connections
               (paper_id, theory_a, theory_b, connection_type,
                formula_a_id, formula_b_id, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (conn_obj.paper_id, conn_obj.theory_a, conn_obj.theory_b,
             conn_obj.connection_type, conn_obj.formula_a_id,
             conn_obj.formula_b_id, conn_obj.description),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_all_claimed_connections(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM claimed_connections"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Conjectures ──────────────────────────────────────────────

    def insert_conjecture(self, c: Conjecture) -> int:
        cur = self.conn.execute(
            """INSERT INTO conjectures
               (conjecture_type, title, statement_latex, statement_natural,
                theories_involved, evidence_formula_ids, evidence_paper_ids,
                algebraic_verified, numerical_verified, dimensional_verified,
                counterexample_found, is_novel, evidence_score,
                significance_score, combined_score, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (c.conjecture_type, c.title, c.statement_latex, c.statement_natural,
             json.dumps(c.theories_involved), json.dumps(c.evidence_formula_ids),
             json.dumps(c.evidence_paper_ids), 
             _boolint(c.algebraic_verified), _boolint(c.numerical_verified),
             _boolint(c.dimensional_verified), _boolint(c.counterexample_found),
             _boolint(c.is_novel), c.evidence_score, c.significance_score,
             c.combined_score, c.status, c.notes),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_conjectures(self, status: str | None = None) -> list[dict]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM conjectures WHERE status = ? ORDER BY combined_score DESC",
                (status,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM conjectures ORDER BY combined_score DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_conjecture_verification(
        self, conj_id: int, 
        algebraic: bool | None = None,
        numerical: bool | None = None,
        dimensional: bool | None = None,
        counterexample: bool | None = None,
        is_novel: bool | None = None,
        status: str | None = None,
    ):
        updates = []
        values = []
        if algebraic is not None:
            updates.append("algebraic_verified = ?")
            values.append(int(algebraic))
        if numerical is not None:
            updates.append("numerical_verified = ?")
            values.append(int(numerical))
        if dimensional is not None:
            updates.append("dimensional_verified = ?")
            values.append(int(dimensional))
        if counterexample is not None:
            updates.append("counterexample_found = ?")
            values.append(int(counterexample))
        if is_novel is not None:
            updates.append("is_novel = ?")
            values.append(int(is_novel))
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if updates:
            values.append(conj_id)
            self.conn.execute(
                f"UPDATE conjectures SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            self.conn.commit()

    # ── Stats ────────────────────────────────────────────────────

    def summary(self) -> dict:
        return {
            "papers": self.count_papers(),
            "formulas": self.count_formulas(),
            "predictions": self.conn.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],
            "claimed_connections": self.conn.execute("SELECT COUNT(*) FROM claimed_connections").fetchone()[0],
            "conjectures": self.conn.execute("SELECT COUNT(*) FROM conjectures").fetchone()[0],
            "formulas_by_theory": {
                row["theory_slug"]: row["cnt"]
                for row in self.conn.execute(
                    "SELECT theory_slug, COUNT(*) as cnt FROM formulas GROUP BY theory_slug"
                ).fetchall()
            },
        }

    def close(self):
        self.conn.close()


def _boolint(v: bool | None) -> int | None:
    return int(v) if v is not None else None
