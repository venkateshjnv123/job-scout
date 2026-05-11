"""Tests for SQLite dedup store."""

from __future__ import annotations

from pathlib import Path

import pytest

from radar.dedup import SeenStore
from radar.models import JobPosting


def _make_posting(uid: str, url: str) -> JobPosting:
    return JobPosting(
        id=uid, title="Engineer", company="Co", url=url,
        location="Remote", body="Java remote", source="test"
    )


def test_new_postings_pass_through(tmp_path: Path) -> None:
    db = str(tmp_path / "seen.db")
    with SeenStore(db) as store:
        postings = [_make_posting("1", "http://a.com"), _make_posting("2", "http://b.com")]
        result = store.filter_new(postings)
        assert len(result) == 2


def test_seen_postings_filtered(tmp_path: Path) -> None:
    db = str(tmp_path / "seen.db")
    with SeenStore(db) as store:
        p = _make_posting("1", "http://a.com")
        store.mark_seen([p])
        result = store.filter_new([p])
        assert len(result) == 0


def test_mixed_new_and_seen(tmp_path: Path) -> None:
    db = str(tmp_path / "seen.db")
    with SeenStore(db) as store:
        old = _make_posting("1", "http://old.com")
        new = _make_posting("2", "http://new.com")
        store.mark_seen([old])
        result = store.filter_new([old, new])
        assert len(result) == 1
        assert result[0].id == "2"


def test_persists_across_instances(tmp_path: Path) -> None:
    db = str(tmp_path / "seen.db")
    p = _make_posting("1", "http://persist.com")

    with SeenStore(db) as store:
        store.mark_seen([p])

    with SeenStore(db) as store2:
        result = store2.filter_new([p])
        assert len(result) == 0
