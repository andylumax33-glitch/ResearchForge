"""Filesystem artifact storage with traversal protection and reproducible export."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from researchforge.models import Artifact, ResearchProject


class UnsafeArtifactPathError(ValueError):
    pass


def _safe_path(root: Path, relative_path: str) -> Path:
    candidate = PurePosixPath(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in relative_path:
        raise UnsafeArtifactPathError("artifact path must remain inside the artifact store")
    resolved_root = root.resolve()
    resolved_path = (root / Path(*candidate.parts)).resolve()
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise UnsafeArtifactPathError("artifact path escapes the artifact store")
    return resolved_path


class FileArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, relative_path: str, content: bytes, *, kind: str) -> Artifact:
        logical_path = PurePosixPath(relative_path)
        checksum = hashlib.sha256(content).hexdigest()
        stored_path = str(logical_path.parent / f"{checksum}-{logical_path.name}")
        destination = _safe_path(self.root, stored_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != content:
                raise ValueError("content-addressed artifact collision")
        else:
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=".researchforge-", dir=destination.parent
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(file_descriptor, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        return Artifact(
            kind=kind,
            path=stored_path,
            checksum=checksum,
        )

    def get_bytes(self, artifact: Artifact) -> bytes:
        source = _safe_path(self.root, artifact.path)
        content = source.read_bytes()
        actual_checksum = hashlib.sha256(content).hexdigest()
        if actual_checksum != artifact.checksum:
            raise ValueError(f"artifact checksum mismatch: {artifact.path}")
        return content

    def export_project(self, project: ResearchProject, destination: Path) -> Path:
        resolved_destination = destination.resolve()
        resolved_root = self.root.resolve()
        if resolved_destination == resolved_root or resolved_root in resolved_destination.parents:
            raise UnsafeArtifactPathError("export destination must be outside the artifact store")
        destination.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=".researchforge-export-", suffix=".zip", dir=destination.parent
        )
        os.close(file_descriptor)
        temporary = Path(temporary_name)
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                manifest = json.dumps(project.model_dump(mode="json"), indent=2, sort_keys=True)
                archive.writestr("manifest.json", manifest)
                for artifact in sorted(project.artifacts, key=lambda item: item.path):
                    archive.writestr(f"artifacts/{artifact.path}", self.get_bytes(artifact))
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination
