"""Scout records, spatial coverage and export snapshots."""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

from .errors import ScoutError
from .files import identifier, now
from .geometry import number
from .files import atomic_json
from .geometry import cell


class Library:
    def __init__(self, root: Path):
        root = root.expanduser().resolve()
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "scout.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS records(
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL,
                    created_at TEXT NOT NULL, updated_at TEXT NOT NULL, data TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS record_kind ON records(kind);
                CREATE TABLE IF NOT EXISTS coverage(
                    cell TEXT NOT NULL, heading INTEGER NOT NULL, visits INTEGER NOT NULL,
                    last_at TEXT NOT NULL, PRIMARY KEY(cell,heading));
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, kind, name, data, record_id=None):
        rid = record_id or identifier(kind)
        with self.connect() as db:
            db.execute(
                """INSERT INTO records VALUES(?,?,?,?,?,?) ON CONFLICT(id)
                DO UPDATE SET name=excluded.name,updated_at=excluded.updated_at,data=excluded.data""",
                (rid, kind, name, now(), now(), json.dumps(data, allow_nan=False)),
            )
        return self.get(rid)

    def get(self, rid):
        with self.connect() as db:
            row = db.execute(
                "SELECT id,kind,name,created_at,updated_at,data FROM records WHERE id=?",
                (rid,),
            ).fetchone()
        if row is None:
            raise ScoutError(f"Unknown library ID: {rid}")
        return self._record(row)

    @staticmethod
    def _record(row):
        keys = ("id", "kind", "name", "created_at", "updated_at", "data")
        return dict(zip(keys, (*row[:5], json.loads(row[5]))))

    def list(self, kind=None, query="", limit=50):
        limit = int(number(limit, 1, 200, "limit"))
        with self.connect() as db:
            rows = db.execute(
                """SELECT id,kind,name,created_at,updated_at,data FROM records WHERE (? IS NULL OR kind=?)
                AND (instr(lower(name),lower(?))>0 OR instr(lower(data),lower(?))>0)
                ORDER BY updated_at DESC LIMIT ?""",
                (kind, kind, query, query, limit),
            ).fetchall()
        return [self._record(row) for row in rows]

    def visit(self, pose):
        heading = int((pose["yaw"] % 360) / 45)
        with self.connect() as db:
            db.execute(
                """INSERT INTO coverage VALUES(?,?,1,?) ON CONFLICT(cell,heading)
                DO UPDATE SET visits=visits+1,last_at=excluded.last_at""",
                (cell(pose), heading, now()),
            )

    def visits(self, pose):
        with self.connect() as db:
            return db.execute(
                "SELECT coalesce(sum(visits),0) FROM coverage WHERE cell=?",
                (cell(pose),),
            ).fetchone()[0]

    def coverage(self, limit=200):
        limit = int(number(limit, 1, 1000, "limit"))
        with self.connect() as db:
            rows = [
                dict(zip(("cell", "heading", "visits", "last_at"), r))
                for r in db.execute(
                    "SELECT * FROM coverage ORDER BY last_at DESC LIMIT ?", (limit,)
                )
            ]
            total = db.execute(
                "SELECT count(DISTINCT cell),coalesce(sum(visits),0) FROM coverage"
            ).fetchone()
        return {
            "cell_size_m": 8,
            "heading_sector_degrees": 45,
            "unique_cells": total[0],
            "total_visits": total[1],
            "cells": rows,
        }

    def export(self):
        with self.connect() as db:
            db.execute("BEGIN")
            records = [
                self._record(row)
                for row in db.execute(
                    "SELECT id,kind,name,created_at,updated_at,data FROM records ORDER BY created_at"
                )
            ]
            coverage = [
                dict(zip(("cell", "heading", "visits", "last_at"), r))
                for r in db.execute("SELECT * FROM coverage")
            ]
        destination = self.root / "exports" / f"{identifier('scout')}.json"
        atomic_json(
            destination,
            {
                "schema_version": 1,
                "exported_at": now(),
                "records": records,
                "coverage": coverage,
            },
        )
        return str(destination)
