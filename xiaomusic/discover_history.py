"""探索式播放的收听历史：记录已推荐过的歌单和歌曲，用于"不重样"

存成一个 JSON 文件，容量有上限（先进先出），条目超过保留天数后视为没听过。
"""

import json
import os
import time
from collections import OrderedDict


class DiscoverHistory:
    def __init__(self, path, max_sheets=300, max_songs=3000, ttl_days=90, log=None):
        self.path = path
        self.max_sheets = max_sheets
        self.max_songs = max_songs
        self.ttl = ttl_days * 86400 if ttl_days and ttl_days > 0 else 0
        self.log = log
        self.sheets = OrderedDict()  # key -> 时间戳
        self.songs = OrderedDict()
        self._load()

    # ---------- 读写 ----------
    def _warn(self, msg):
        if self.log:
            self.log.warning(msg)

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            for name in ("sheets", "songs"):
                target = getattr(self, name)
                for key, ts in data.get(name, []):
                    target[str(key)] = float(ts)
        except FileNotFoundError:
            return
        except Exception as e:
            self._warn(f"探索历史文件读取失败，已忽略并重新开始: {e}")
            self.sheets.clear()
            self.songs.clear()
            return
        self._prune()

    def save(self):
        """原子写入，失败只记日志，不影响播放"""
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "sheets": list(self.sheets.items()),
                        "songs": list(self.songs.items()),
                    },
                    f,
                    ensure_ascii=False,
                )
            os.replace(tmp, self.path)
        except Exception as e:
            self._warn(f"探索历史文件保存失败: {e}")

    def _prune(self):
        now = time.time()
        for store, limit in (
            (self.sheets, self.max_sheets),
            (self.songs, self.max_songs),
        ):
            if self.ttl:
                for key in [k for k, ts in store.items() if now - ts > self.ttl]:
                    del store[key]
            while len(store) > limit:
                store.popitem(last=False)

    # ---------- 查询 / 记录 ----------
    def _seen(self, store, key):
        ts = store.get(key)
        if ts is None:
            return False
        if self.ttl and time.time() - ts > self.ttl:
            return False
        return True

    def has_sheet(self, key):
        return self._seen(self.sheets, key)

    def has_song(self, key):
        return self._seen(self.songs, key)

    def add_sheet(self, key):
        self.sheets[key] = time.time()
        self.sheets.move_to_end(key)
        self._prune()

    def add_songs(self, keys):
        now = time.time()
        for key in keys:
            self.songs[key] = now
            self.songs.move_to_end(key)
        self._prune()

    def clear(self):
        self.sheets.clear()
        self.songs.clear()
        self.save()
