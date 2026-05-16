"""Cheap, mechanical invariants that catch the kind of mistake we keep
making by hand.

Goal: every commit batch that completes a roadmap phase must also update
the README roadmap row for that phase to ``done``. The Phase 2 and Phase 3
self-reviews both caught the same drift after the fact; this test makes
the loop close inside ``pytest`` instead.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"

ROADMAP_ROW = re.compile(r"^\|\s*(\d+)\s*\|.*\|\s*(done|planned|in progress)\s*\|", re.IGNORECASE)


def _phase_status_from_readme() -> dict[int, str]:
    statuses: dict[int, str] = {}
    for line in README.read_text(encoding="utf-8").splitlines():
        m = ROADMAP_ROW.match(line)
        if m:
            statuses[int(m.group(1))] = m.group(2).lower()
    return statuses


def _phase_commits_count() -> dict[int, int]:
    """How many commits on `main` reference each Phase number?

    A commit body mentioning ``Phase N`` (in the subject or body) is taken
    as evidence that Phase N has been worked on. The very first commit
    that mentions ``Phase N`` is enough to trip the invariant: by the
    time you ship a follow-up commit, the roadmap should already read
    ``done``.
    """
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "log", "--format=%B%x00", "--all"],
        check=True,
        capture_output=True,
        text=True,
    )
    counts: dict[int, int] = {}
    for entry in result.stdout.split("\0"):
        for phase in re.findall(r"\bPhase\s+(\d+)\b", entry):
            counts[int(phase)] = counts.get(int(phase), 0) + 1
    return counts


def test_readme_roadmap_marks_completed_phases_done():
    statuses = _phase_status_from_readme()
    commit_counts = _phase_commits_count()
    assert statuses, "README roadmap table not detected — has the format changed?"

    # A phase whose commit history references it must not still be 'planned'.
    # 'in progress' is acceptable transiently; 'planned' is the failure case.
    stale = [
        (phase, statuses[phase])
        for phase, n in commit_counts.items()
        if phase in statuses and statuses[phase] == "planned" and n >= 2
        # n >= 2 lets Phase N appear as the *target* of a single commit
        # before its README row needs to flip. By the time a fix-up
        # commit for the same phase lands, the row must say `done`.
    ]
    assert not stale, (
        f"README roadmap claims these phases are still 'planned' even though "
        f"two or more commits already reference them: {stale}. "
        "Flip the roadmap row(s) to 'done' before merging."
    )


def test_readme_links_to_bft_note():
    """The README's Security model must link to docs/BFT_NOTE.md."""
    text = README.read_text(encoding="utf-8")
    assert "docs/BFT_NOTE.md" in text, (
        "README must link to docs/BFT_NOTE.md so single-file readers see the "
        "single-provider honesty note."
    )


def test_readme_has_non_affiliation_disclaimer():
    """The README must always carry the DeepMind non-affiliation line."""
    text = README.read_text(encoding="utf-8")
    assert "not affiliated with" in text.lower()
    assert "deepmind" in text.lower()


def test_readme_has_sunset_clause():
    """The README must always carry the sunset/archive condition."""
    text = README.read_text(encoding="utf-8").lower()
    assert "sunset" in text or "archived" in text
