"""Artifact registry (MANIFEST.json) for SyFlow runs.

Every file produced during a run is registered with its hash, producer,
and bidirectional claim linkage. Verification re-hashes artifacts against
the manifest to detect tampering or drift.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class ArtifactEntry:
    """A single artifact in the run manifest."""

    def __init__(
        self,
        path: str,
        kind: str = "other",
        produced_by: Optional[str] = None,
        description: Optional[str] = None,
        tool_use_id: Optional[str] = None,
    ):
        self.path = path
        self.kind = kind  # figure, table, code, data, report, batch_record, other
        self.produced_by = produced_by
        self.description = description
        self.tool_use_id = tool_use_id
        self.cited_by: list[str] = []
        self.sha256: Optional[str] = None
        self.bytes: int = 0
        self.produced_at = datetime.now(timezone.utc).isoformat()
        self.modified_at = self.produced_at
        self.mtime_ns: int = 0

    def compute_hash(self, base_dir: Path) -> str:
        full_path = base_dir / self.path
        if full_path.exists():
            h = hashlib.sha256()
            with open(full_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            self.sha256 = h.hexdigest()
            stat = full_path.stat()
            self.bytes = stat.st_size
            self.mtime_ns = stat.st_mtime_ns
        return self.sha256 or ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "produced_by": self.produced_by,
            "produced_at": self.produced_at,
            "modified_at": self.modified_at,
            "mtime_ns": self.mtime_ns,
            "tool_use_id": self.tool_use_id,
            "description": self.description,
            "cited_by": self.cited_by,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ArtifactEntry":
        entry = cls(
            path=d["path"],
            kind=d.get("kind", "other"),
            produced_by=d.get("produced_by"),
            description=d.get("description"),
            tool_use_id=d.get("tool_use_id"),
        )
        entry.sha256 = d.get("sha256")
        entry.bytes = d.get("bytes", 0)
        entry.produced_at = d.get("produced_at", "")
        entry.modified_at = d.get("modified_at", "")
        entry.mtime_ns = d.get("mtime_ns", 0)
        entry.cited_by = d.get("cited_by", [])
        return entry


class RunManifest:
    """Artifact registry for a single run."""

    def __init__(self, run_dir: str | Path):
        self.run_dir = Path(run_dir)
        self.manifest_path = self.run_dir / "MANIFEST.json"
        self.artifacts: dict[str, ArtifactEntry] = {}

    def register(
        self,
        path: str,
        kind: str = "other",
        produced_by: Optional[str] = None,
        description: Optional[str] = None,
        tool_use_id: Optional[str] = None,
    ) -> ArtifactEntry:
        entry = ArtifactEntry(
            path=path,
            kind=kind,
            produced_by=produced_by,
            description=description,
            tool_use_id=tool_use_id,
        )
        entry.compute_hash(self.run_dir)
        self.artifacts[path] = entry
        self.save()
        return entry

    def link_claim(self, path: str, claim_id: str) -> None:
        if path in self.artifacts:
            if claim_id not in self.artifacts[path].cited_by:
                self.artifacts[path].cited_by.append(claim_id)
                self.save()

    def get(self, path: str) -> Optional[ArtifactEntry]:
        return self.artifacts.get(path)

    def has_path(self, path: str) -> bool:
        return path in self.artifacts

    def verify_all(self) -> list[dict]:
        """Re-hash all artifacts and report mismatches."""
        issues = []
        for path, entry in self.artifacts.items():
            full_path = self.run_dir / path
            if not full_path.exists():
                issues.append({"path": path, "issue": "missing", "expected_sha256": entry.sha256})
                continue
            h = hashlib.sha256()
            with open(full_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            current = h.hexdigest()
            if current != entry.sha256:
                issues.append({
                    "path": path,
                    "issue": "hash_mismatch",
                    "expected": entry.sha256,
                    "actual": current,
                })
        return issues

    def save(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "run_dir": str(self.run_dir),
            "artifact_count": len(self.artifacts),
            "artifacts": {k: v.to_dict() for k, v in self.artifacts.items()},
        }
        with open(self.manifest_path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, run_dir: str | Path) -> "RunManifest":
        manifest = cls(run_dir)
        if manifest.manifest_path.exists():
            with open(manifest.manifest_path) as f:
                data = json.load(f)
            for path, entry_data in data.get("artifacts", {}).items():
                manifest.artifacts[path] = ArtifactEntry.from_dict(entry_data)
        return manifest

    @classmethod
    def create(cls, run_dir: str | Path) -> "RunManifest":
        """Create a new run directory with manifest skeleton."""
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "work").mkdir(exist_ok=True)
        (run_dir / "inputs").mkdir(exist_ok=True)
        manifest = cls(run_dir)
        manifest.save()
        return manifest
