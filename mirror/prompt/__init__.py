from __future__ import annotations

from pathlib import Path

FRIEND_BIO = (Path(__file__).parent /
              "friend_bio.md").read_text(encoding="utf-8")
GROUP_BIO = (Path(__file__).parent /
             "group_bio.md").read_text(encoding="utf-8")
SUMMARY_BIO = (Path(__file__).parent /
               "summary_bio.md").read_text(encoding="utf-8")

COMPACT = (Path(__file__).parent / "compact.md").read_text(encoding="utf-8")
