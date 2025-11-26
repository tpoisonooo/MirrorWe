import importlib.util, os, sys
from core.person import Person

class FriendRegistry:
    def __init__(self, folder="friends"):
        self.folder = folder
        self._cache = {}

    def get(self, wxid: str) -> Person:
        if wxid in self._cache:
            return self._cache[wxid]
        path = os.path.join(self.folder, f"friend_{wxid}.py")
        if not os.path.exists(path):
            raise FileNotFoundError(f"No friend file for {wxid}")
        spec = importlib.util.spec_from_file_location(f"friend_{wxid}", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[f"friend_{wxid}"] = mod
        spec.loader.exec_module(mod)
        cls = getattr(mod, f"Friend_{wxid}")
        inst = cls()
        self._cache[wxid] = inst
        return inst

    def reload(self, wxid: str):
        self._cache.pop(wxid, None)
        return self.get(wxid)