from __future__ import annotations

import json
from pathlib import Path

import pytest

from researchforge.artifacts import FileArtifactStore, UnsafeArtifactPathError
from researchforge.logging_utils import structured_event


@pytest.mark.parametrize("path", ["../secret.txt", "a/../../secret.txt", "/tmp/secret.txt"])
def test_artifact_store_blocks_path_traversal(tmp_path: Path, path: str) -> None:
    store = FileArtifactStore(tmp_path / "artifacts")

    with pytest.raises(UnsafeArtifactPathError):
        store.put_bytes(path, b"secret", kind="test")
    assert not (tmp_path / "secret.txt").exists()


def test_structured_logging_redacts_sensitive_values() -> None:
    output = structured_event(
        "provider request",
        safe="visible",
        **{
            "api_key": "example-credential-value",
            "authorization": "Bearer example-authorization-value",
        },
    )

    record = json.loads(output)
    assert "example-credential-value" not in output
    assert "example-authorization-value" not in output
    assert record["api_key"] == "[REDACTED]"
    assert record["authorization"] == "[REDACTED]"
    assert record["safe"] == "visible"


def test_modified_artifact_fails_integrity_check(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path / "artifacts")
    artifact = store.put_bytes("project/result.txt", b"verified", kind="result")
    (store.root / artifact.path).write_bytes(b"tampered")

    with pytest.raises(ValueError, match="checksum mismatch"):
        store.get_bytes(artifact)


def test_artifact_paths_are_content_addressed_and_not_overwritten(tmp_path: Path) -> None:
    store = FileArtifactStore(tmp_path / "artifacts")
    first = store.put_bytes("project/result.txt", b"first", kind="result")
    second = store.put_bytes("project/result.txt", b"second", kind="result")

    assert first.path != second.path
    assert store.get_bytes(first) == b"first"
    assert store.get_bytes(second) == b"second"
