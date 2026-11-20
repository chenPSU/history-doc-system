import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import new_episode  # noqa: E402


def test_from_csv_creates_32_folders_and_never_overwrites(tmp_path):
    made = new_episode.from_csv(ROOT / "data" / "episodes.csv", root=tmp_path)
    assert len(made) == 32
    assert all(new for _, new in made)
    brief = (tmp_path / "2026-12-07-th-indochina-war-1940" / "brief.yaml").read_text(encoding="utf-8")
    assert "th_only: true" in brief
    again = new_episode.from_csv(ROOT / "data" / "episodes.csv", root=tmp_path)
    assert not any(new for _, new in again)
