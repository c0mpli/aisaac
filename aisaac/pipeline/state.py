"""
Pipeline State Tracker.

Makes the AIsaac pipeline resumable. If the process crashes
(API timeout, OOM, power loss, etc.), it restarts from where
it left off instead of re-doing everything.

State is stored as a JSON file alongside the database.
Each phase records its completion status and key checkpoints.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import DATA_DIR

log = logging.getLogger(__name__)

STATE_PATH = DATA_DIR / "pipeline_state.json"


class PipelineState:
    """Track pipeline progress for resume capability."""

    PHASES = [
        "ingest_tier1",
        "ingest_tier2",
        "ingest_tier3",
        "ingest_bridges",
        "extract",
        "deduplicate",
        "citation_graph",
        "compare",
        "ml_embed",
        "ml_cluster",
        "ml_universality",
        "ml_anomaly",
        "conjecture_from_comparisons",
        "conjecture_from_clusters",
        "conjecture_from_universality",
        "conjecture_from_anomalies",
        "verify",
        "visualize",
        "report",
        "paper_draft",
    ]

    def __init__(self, path: Path | None = None):
        self.path = path or STATE_PATH
        self.state: dict = {
            "phases": {},
            "started_at": None,
            "last_updated": None,
            "config": {},
        }
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self.state = json.loads(self.path.read_text())
                log.info(f"Loaded pipeline state from {self.path}")
            except Exception as e:
                log.warning(f"Failed to load state: {e}, starting fresh")

    def _save(self):
        self.state["last_updated"] = datetime.now().isoformat()
        self.path.write_text(json.dumps(self.state, indent=2))

    def is_completed(self, phase: str) -> bool:
        """Check if a phase has been completed."""
        return self.state.get("phases", {}).get(phase, {}).get("status") == "completed"

    def mark_started(self, phase: str):
        """Mark a phase as started."""
        if "phases" not in self.state:
            self.state["phases"] = {}
        self.state["phases"][phase] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
        }
        if not self.state.get("started_at"):
            self.state["started_at"] = datetime.now().isoformat()
        self._save()

    def mark_completed(self, phase: str, details: dict | None = None):
        """Mark a phase as completed with optional details."""
        self.state["phases"][phase] = {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "details": details or {},
        }
        self._save()

    def mark_failed(self, phase: str, error: str):
        """Mark a phase as failed."""
        self.state["phases"][phase] = {
            "status": "failed",
            "failed_at": datetime.now().isoformat(),
            "error": error,
        }
        self._save()

    def set_checkpoint(self, phase: str, key: str, value):
        """Set a checkpoint within a phase (e.g., last processed paper ID)."""
        if phase not in self.state.get("phases", {}):
            self.state.setdefault("phases", {})[phase] = {"status": "running"}
        self.state["phases"][phase].setdefault("checkpoints", {})[key] = value
        self._save()

    def get_checkpoint(self, phase: str, key: str, default=None):
        """Get a checkpoint value."""
        return (
            self.state.get("phases", {})
            .get(phase, {})
            .get("checkpoints", {})
            .get(key, default)
        )

    def get_next_phase(self) -> Optional[str]:
        """Get the next phase that hasn't been completed."""
        for phase in self.PHASES:
            if not self.is_completed(phase):
                return phase
        return None

    def summary(self) -> str:
        """Human-readable summary of pipeline state."""
        lines = ["Pipeline State:"]
        for phase in self.PHASES:
            info = self.state.get("phases", {}).get(phase, {})
            status = info.get("status", "pending")
            icon = {"completed": "✓", "running": "→", "failed": "✗", "pending": "○"}.get(status, "?")
            extra = ""
            if status == "completed" and "details" in info:
                d = info["details"]
                if isinstance(d, dict):
                    extras = [f"{k}={v}" for k, v in d.items() if not k.startswith("_")]
                    extra = f" ({', '.join(extras[:3])})" if extras else ""
            elif status == "failed":
                extra = f" ERROR: {info.get('error', '?')[:60]}"
            lines.append(f"  {icon} {phase}{extra}")
        return "\n".join(lines)

    def reset(self):
        """Reset all state (start fresh)."""
        self.state = {
            "phases": {},
            "started_at": None,
            "last_updated": None,
            "config": {},
        }
        self._save()
        log.info("Pipeline state reset")
