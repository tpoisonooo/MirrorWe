from datetime import datetime
from typing import Any

from .inner import Inner


class MemoryStream:

    def __init__(self):
        self.private: list[Inner] = []
        self.group: list[Inner] = []
        self.moment: list[dict[str, Any]] = []

    def __len__(self):
        return len(self.private) + len(self.group) + len(self.moment)

    def __bool__(self):
        return bool(self.private or self.group or self.moment)

    def __iter__(self):
        return iter(self.private + self.group + self.moment)

    def add(self,
            private: Inner = None,
            group: Inner = None,
            moment: dict[str, Any] = None):
        if private:
            self.private.append(private)
        if group:
            self.group.append(group)
        if moment:
            self.moment.append(moment)

    def recent(self, days=7):
        cutoff = datetime.now().timestamp() - days * 86400
        return [
            m for m in self.private + self.group + self.moment
            if m["ts"].timestamp() > cutoff
        ]

    def today(self):
        import datetime as dt
        today = dt.date.today()
        return [
            m for m in self.private + self.group + self.moment
            if m["ts"].date() == today
        ]
