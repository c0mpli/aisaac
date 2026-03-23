"""Symptom taxonomy for detecting wrong premises in scientific frameworks.

Defines the classification system for symptoms that historically preceded
paradigm shifts, along with the types of premise errors those symptoms indicated.
"""

from dataclasses import dataclass, field
from enum import Enum, auto


class SymptomType(Enum):
    """Categories of anomalous patterns that signal a wrong premise."""

    EPICYCLE_ACCUMULATION = auto()
    """Framework requires growing number of ad-hoc patches to fit observations."""

    UNEXPLAINED_COINCIDENCE = auto()
    """Two quantities match or correlate with no reason from current theory."""

    STRUCTURED_OBSTACLE = auto()
    """Calculations systematically diverge or break in a patterned way."""

    UNIVERSAL_QUANTITY = auto()
    """A constant or ratio appears across unrelated domains."""

    UNEXPLAINED_VALUE = auto()
    """A fundamental parameter has no derivation; its value is just measured."""

    NULL_RESULT = auto()
    """An experiment designed to detect an effect consistently finds nothing."""

    FRAMEWORK_MISMATCH = auto()
    """Two successful theories give contradictory answers in overlap regimes."""

    DUAL_DESCRIPTION = auto()
    """The same physics can be described by two seemingly different theories."""

    PROLIFERATION_WITHOUT_SELECTION = auto()
    """A framework generates many solutions with no principle to select the physical one."""


class PremiseErrorType(Enum):
    """Categories of wrong premises that generate symptoms."""

    UNNECESSARY_ASSUMPTION = auto()
    """An assumed entity or structure does not exist (e.g., luminiferous ether)."""

    MISIDENTIFIED_FUNDAMENTAL = auto()
    """What is taken as fundamental is actually derived or emergent."""

    FALSE_DICHOTOMY = auto()
    """Two things treated as distinct are actually aspects of one thing."""

    WRONG_LEVEL_OF_DESCRIPTION = auto()
    """The theory operates at the wrong level of abstraction."""

    INVERTED_CAUSATION = auto()
    """Cause and effect are swapped; the actual driver is misidentified."""

    IMPLICIT_BACKGROUND = auto()
    """A structure treated as fixed background is actually dynamical."""

    CONTINUITY_ASSUMPTION = auto()
    """Something assumed continuous is actually discrete, or vice versa."""


@dataclass
class Symptom:
    """A specific anomaly observed before a paradigm shift."""

    symptom_type: SymptomType
    description: str
    evidence: list[str]
    confidence: float
    affected_quantity: str
    theories_involved: list[str]


@dataclass
class PremiseShiftRecord:
    """A historical record of a scientific premise being overturned."""

    field: str
    year: int
    person: str
    old_premise: str
    new_premise: str
    premise_error_type: PremiseErrorType
    symptoms_before: list[Symptom]
    time_stuck_years: int
    time_to_solve_after: int
    key_insight: str
    what_made_it_hard: str
    trigger: str
    succeeded: bool = True
