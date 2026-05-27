"""Tests for the JSONL logbook + SQLite mirror."""

from __future__ import annotations

import json

from control.logbook import Logbook


def test_logbook_append_writes_jsonl(tmp_path):
    lb = Logbook(tmp_path)
    entry = {
        "id": "abc",
        "x": 1.0,
        "y": 2.0,
        "z": 0.0,
        "outcome": "glitch",
        "verdict": {"fault": True, "heartbeat_alive": True, "campaign_complete": False},
    }
    stored = lb.append(entry)
    assert stored["id"] == "abc"
    # File written
    files = list(tmp_path.glob("logbook-*.jsonl"))
    assert len(files) == 1
    content = files[0].read_text().strip()
    assert json.loads(content)["id"] == "abc"


def test_logbook_read_filters_by_outcome(tmp_path):
    lb = Logbook(tmp_path)
    lb.append({"id": "a", "outcome": "glitch", "x": 0, "y": 0})
    lb.append({"id": "b", "outcome": "hang", "x": 0, "y": 0})
    lb.append({"id": "c", "outcome": "glitch", "x": 1, "y": 1})
    glitches = lb.read(outcome="glitch")
    assert {e["id"] for e in glitches} == {"a", "c"}


def test_logbook_sqlite_mirror_contains_appended_rows(tmp_path):
    lb = Logbook(tmp_path)
    lb.append({"id": "a", "outcome": "glitch", "x": 1.0, "y": 2.0, "z": 0.0})
    lb.append({"id": "b", "outcome": "nothing", "x": 1.0, "y": 2.0, "z": 0.0})
    rows = lb.heatmap(outcome="glitch")
    assert rows == [{"x": 1.0, "y": 2.0, "count": 1}]


def test_logbook_get_by_id(tmp_path):
    lb = Logbook(tmp_path)
    lb.append({"id": "needle", "outcome": "glitch", "x": 1, "y": 1})
    lb.append({"id": "hay", "outcome": "nothing", "x": 0, "y": 0})
    found = lb.get("needle")
    assert found is not None
    assert found["id"] == "needle"
