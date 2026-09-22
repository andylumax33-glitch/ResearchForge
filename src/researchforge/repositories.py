"""SQLite implementation of optimistic, atomic state persistence."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import UUID

from researchforge.models import Checkpoint, ResearchProject


class ProjectNotFoundError(LookupError):
    pass


class ConcurrentUpdateError(RuntimeError):
    pass


class SQLiteStateRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                    CREATE TABLE IF NOT EXISTS projects (
                        project_id TEXT PRIMARY KEY,
                        version INTEGER NOT NULL,
                        payload TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        checkpoint_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES projects(project_id)
                    );
                    """
            )

    def create(self, project: ResearchProject) -> None:
        try:
            with closing(self._connect()) as connection, connection:
                connection.execute(
                    "INSERT INTO projects(project_id, version, payload) VALUES (?, ?, ?)",
                    (str(project.project_id), project.version, project.model_dump_json()),
                )
        except sqlite3.IntegrityError as error:
            raise ConcurrentUpdateError(f"project {project.project_id} already exists") from error

    def get(self, project_id: UUID) -> ResearchProject:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM projects WHERE project_id = ?", (str(project_id),)
            ).fetchone()
        if row is None:
            raise ProjectNotFoundError(str(project_id))
        return ResearchProject.model_validate_json(row[0])

    def save(self, project: ResearchProject, *, expected_version: int) -> None:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE projects SET version = ?, payload = ? WHERE project_id = ? AND version = ?",
                (
                    project.version,
                    project.model_dump_json(),
                    str(project.project_id),
                    expected_version,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrentUpdateError("project changed since it was loaded")

    def save_transition(
        self, project: ResearchProject, checkpoint: Checkpoint, *, expected_version: int
    ) -> None:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "UPDATE projects SET version = ?, payload = ? WHERE project_id = ? AND version = ?",
                (
                    project.version,
                    project.model_dump_json(),
                    str(project.project_id),
                    expected_version,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrentUpdateError("project changed since it was loaded")
            connection.execute(
                "INSERT INTO checkpoints(checkpoint_id, project_id, payload) VALUES (?, ?, ?)",
                (
                    str(checkpoint.checkpoint_id),
                    str(checkpoint.project_id),
                    checkpoint.model_dump_json(),
                ),
            )

    def get_checkpoint(self, checkpoint_id: UUID) -> Checkpoint:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM checkpoints WHERE checkpoint_id = ?",
                (str(checkpoint_id),),
            ).fetchone()
        if row is None:
            raise ProjectNotFoundError(f"checkpoint {checkpoint_id}")
        return Checkpoint.model_validate_json(row[0])
