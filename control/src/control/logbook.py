"""Append-only JSONL log of glitch attempts + SQLite query mirror.

JSONL stays canonical. SQLite is rebuildable from the JSONL files.

Carry-forward from old-em-setup/glitchweb/backend/app/logbook.py, extended
with the SQLite index per the new spec.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    session TEXT NOT NULL,
    ts TEXT NOT NULL,
    campaign_id TEXT,
    x REAL, y REAL, z REAL,
    delay_us REAL,
    pulse_width_ns REAL,
    voltage_v INTEGER,
    outcome TEXT NOT NULL,
    build_sha TEXT,
    target_pc INTEGER
);
CREATE INDEX IF NOT EXISTS idx_runs_campaign ON runs(campaign_id);
CREATE INDEX IF NOT EXISTS idx_runs_outcome ON runs(outcome);
CREATE INDEX IF NOT EXISTS idx_runs_xy ON runs(x, y);
"""


class Logbook:
    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []
        self._session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        self._sqlite_path = self.log_dir / "index.sqlite"
        self._db_lock = threading.Lock()
        with self._db() as db:
            db.executescript(SQLITE_SCHEMA)

    def _db(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._sqlite_path), isolation_level=None)

    def _path_for_today(self) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        return self.log_dir / f"logbook-{day}.jsonl"

    def add_listener(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        self._listeners.append(fn)

    def append(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        entry = dict(entry)
        entry.setdefault(
            "ts", datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        )
        entry.setdefault("session", self._session_id)

        line = json.dumps(entry, separators=(",", ":")) + "\n"
        with self._lock:
            path = self._path_for_today()
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass

        self._mirror_to_sqlite(entry)

        for fn in list(self._listeners):
            try:
                fn(entry)
            except Exception:
                pass
        return entry

    def _mirror_to_sqlite(self, entry: Dict[str, Any]) -> None:
        with self._db_lock, self._db() as db:
            db.execute(
                """
                INSERT OR REPLACE INTO runs
                (id, session, ts, campaign_id, x, y, z,
                 delay_us, pulse_width_ns, voltage_v, outcome,
                 build_sha, target_pc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.get("id"),
                    entry.get("session"),
                    entry.get("ts"),
                    entry.get("campaign_id"),
                    entry.get("x"),
                    entry.get("y"),
                    entry.get("z"),
                    entry.get("glitch_delay_us"),
                    entry.get("pulse_width_ns"),
                    entry.get("shouter_voltage"),
                    entry.get("outcome"),
                    entry.get("build_sha"),
                    entry.get("target_pc"),
                ),
            )

    def read(
        self,
        since: Optional[str] = None,
        limit: int = 500,
        outcome: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for path in sorted(self.log_dir.glob("logbook-*.jsonl"), reverse=True):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line in reversed(lines):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if outcome and obj.get("outcome") != outcome:
                    continue
                if since and obj.get("ts", "") <= since:
                    continue
                out.append(obj)
                if len(out) >= limit:
                    return list(reversed(out))
        return list(reversed(out))

    def get(self, run_id: str) -> Optional[Dict[str, Any]]:
        for path in sorted(self.log_dir.glob("logbook-*.jsonl"), reverse=True):
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    obj = json.loads(line)
                    if obj.get("id") == run_id:
                        return obj
            except OSError:
                continue
        return None

    def heatmap(
        self,
        campaign_id: Optional[str] = None,
        z: Optional[float] = None,
        outcome: str = "glitch",
    ) -> List[Dict[str, Any]]:
        """GROUP BY (x, y) counting matching outcomes."""
        query = (
            "SELECT x, y, COUNT(*) as count FROM runs "
            "WHERE outcome = ?"
        )
        params: List[Any] = [outcome]
        if campaign_id:
            query += " AND campaign_id = ?"
            params.append(campaign_id)
        if z is not None:
            query += " AND z = ?"
            params.append(z)
        query += " GROUP BY x, y"
        with self._db_lock, self._db() as db:
            rows = db.execute(query, params).fetchall()
        return [{"x": r[0], "y": r[1], "count": r[2]} for r in rows]

    def iter_csv_rows(
        self,
        since: Optional[str] = None,
        outcome: Optional[str] = None,
    ) -> Iterable[Dict[str, Any]]:
        for path in sorted(self.log_dir.glob("logbook-*.jsonl")):
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue
                    if outcome and obj.get("outcome") != outcome:
                        continue
                    if since and obj.get("ts", "") <= since:
                        continue
                    yield obj
            except OSError:
                continue


def default_log_dir() -> Path:
    state = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "share"))
    return state / "emfi-control" / "sessions"
