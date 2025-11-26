from datetime import datetime
from typing import List, Dict, Optional

class MemoryStream:
    def __init__(self):
        self.logs: List[Dict] = []

    def add(self, chat_log=None, moment=None, event=None):
        if chat_log:
            self.logs.append({"type": "chat", "data": chat_log, "ts": datetime.now()})
        if moment:
            self.logs.append({"type": "moment", "data": moment, "ts": datetime.now()})
        if event:
            self.logs.append({"type": "event", "data": event, "ts": datetime.now()})

    def recent(self, days=7):
        cutoff = datetime.now().timestamp() - days * 86400
        return [m for m in self.logs if m["ts"].timestamp() > cutoff]

    def today(self):
        import datetime as dt
        today = dt.date.today()
        return [m for m in self.logs if m["ts"].date() == today]