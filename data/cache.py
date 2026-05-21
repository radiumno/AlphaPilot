"""SQLite 数据持久缓存 — 缓存数据提供者的结果，减少重复网络请求"""

import pickle
import sqlite3
import time
from pathlib import Path
from typing import Optional, Any
from functools import wraps
import pandas as pd
from config.settings import settings


class SQLiteCache:
    """SQLite 键值缓存，支持 TTL 过期"""

    def __init__(self, db_path: Optional[Path] = None, default_ttl: int = 14400):
        self._db_path = db_path or (settings.data_cache_dir / "provider_cache.db")
        self._default_ttl = default_ttl
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    ttl_seconds REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_created ON cache(created_at)")

    def get(self, key: str) -> Optional[Any]:
        """获取缓存，如果过期或不存在返回 None"""
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute(
                "SELECT data, created_at, ttl_seconds FROM cache WHERE key = ?",
                (key,),
            ).fetchone()

        if row is None:
            return None

        data_blob, created_at, ttl = row
        if ttl <= 0 or time.time() - created_at >= ttl:
            self.delete(key)
            return None

        obj = pickle.loads(data_blob)
        # 恢复 pandas 类型
        if isinstance(obj, dict) and obj.get("__pd_series__"):
            return pd.Series(obj["data"], name=obj.get("name"))
        if isinstance(obj, dict) and obj.get("__pd_frame__"):
            return pd.DataFrame(obj["data"])
        return obj

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """写入缓存"""
        if ttl is None:
            ttl = self._default_ttl
        # pandas 对象需要特殊序列化
        if isinstance(value, pd.Series):
            blob = pickle.dumps({
                "__pd_series__": True,
                "data": value.tolist(),
                "name": value.name,
            })
        elif isinstance(value, pd.DataFrame):
            blob = pickle.dumps({
                "__pd_frame__": True,
                "data": value.to_dict("records"),
            })
        else:
            blob = pickle.dumps(value)

        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, data, created_at, ttl_seconds) VALUES (?, ?, ?, ?)",
                (key, blob, time.time(), ttl),
            )

    def delete(self, key: str) -> None:
        """删除单个缓存项"""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))

    def clear_expired(self) -> int:
        """清除所有过期缓存，返回清除数量"""
        with sqlite3.connect(str(self._db_path)) as conn:
            result = conn.execute(
                "DELETE FROM cache WHERE ? - created_at >= ttl_seconds",
                (time.time(),),
            )
            return result.rowcount

    def clear_all(self) -> None:
        """清空全部缓存"""
        with sqlite3.connect(str(self._db_path)) as conn:
            conn.execute("DELETE FROM cache")

    @property
    def size(self) -> int:
        """缓存条目数"""
        with sqlite3.connect(str(self._db_path)) as conn:
            row = conn.execute("SELECT COUNT(*) FROM cache").fetchone()
            return row[0] if row else 0


class CachedProvider:
    """包裹 BaseDataProvider，透明地为每个方法添加缓存

    用法:
        provider = CachedProvider(yfinance_provider, cache)
        # provider 实现了 BaseDataProvider 接口
        nav = provider.get_etf_nav("SPY")  # 首次调用会缓存
    """

    def __init__(self, provider, cache: SQLiteCache, ttl: Optional[int] = None):
        self._provider = provider
        self._cache = cache
        self._ttl = ttl

    def _cache_key(self, method: str, symbol: str) -> str:
        return f"{self._provider.name()}:{method}:{symbol}"

    def name(self) -> str:
        return f"{self._provider.name()}(cached)"

    # ── 缓存代理方法 ─────────────────────────────────────

    def get_etf_nav(self, symbol: str):
        key = self._cache_key("get_etf_nav", symbol)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._provider.get_etf_nav(symbol)
        self._cache.set(key, result, ttl=self._ttl)
        return result

    def get_etf_daily(self, symbol: str, period: str = "1y"):
        key = self._cache_key("get_etf_daily", f"{symbol}:{period}")
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._provider.get_etf_daily(symbol, period)
        self._cache.set(key, result, ttl=self._ttl)
        return result

    def get_fund_nav(self, symbol: str):
        key = self._cache_key("get_fund_nav", symbol)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._provider.get_fund_nav(symbol)
        self._cache.set(key, result, ttl=self._ttl)
        return result

    def get_fund_info(self, symbol: str) -> dict:
        key = self._cache_key("get_fund_info", symbol)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._provider.get_fund_info(symbol)
        self._cache.set(key, result, ttl=self._ttl)
        return result

    def get_fund_holdings(self, symbol: str):
        key = self._cache_key("get_fund_holdings", symbol)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = self._provider.get_fund_holdings(symbol)
        self._cache.set(key, result, ttl=self._ttl)
        return result
