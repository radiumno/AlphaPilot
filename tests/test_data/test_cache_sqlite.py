"""SQLite 持久缓存 + CachedProvider 测试"""

import tempfile
from pathlib import Path
import pandas as pd
import numpy as np
from data.cache import SQLiteCache, CachedProvider


def _make_cache() -> SQLiteCache:
    return SQLiteCache(db_path=Path(tempfile.mktemp(suffix=".db")), default_ttl=3600)


def test_cache_set_get():
    """基本写入和读取"""
    cache = _make_cache()
    cache.set("test:int", 42)
    assert cache.get("test:int") == 42

    cache.set("test:str", "hello")
    assert cache.get("test:str") == "hello"

    cache.set("test:dict", {"a": 1, "b": [2, 3]})
    assert cache.get("test:dict") == {"a": 1, "b": [2, 3]}


def test_cache_miss():
    """不存在的键返回 None"""
    cache = _make_cache()
    assert cache.get("nonexistent") is None


def test_cache_ttl_expiry():
    """TTL 过期后返回 None"""
    cache = _make_cache()
    cache.set("test:expire", "data", ttl=0)  # 立即过期
    assert cache.get("test:expire") is None


def test_cache_delete():
    """删除缓存项"""
    cache = _make_cache()
    cache.set("test:del", "data")
    assert cache.get("test:del") is not None
    cache.delete("test:del")
    assert cache.get("test:del") is None


def test_cache_clear_expired():
    """清除过期缓存"""
    cache = _make_cache()
    cache.set("valid", "keep", ttl=3600)
    cache.set("expired", "gone", ttl=0)
    n = cache.clear_expired()
    assert n >= 1
    assert cache.get("valid") is not None
    assert cache.get("expired") is None


def test_cache_size():
    """缓存条目计数"""
    cache = _make_cache()
    assert cache.size == 0
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.size == 2


def test_cache_clear_all():
    """清空全部缓存"""
    cache = _make_cache()
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear_all()
    assert cache.size == 0


def test_cache_pd_series():
    """缓存和恢复 pd.Series"""
    cache = _make_cache()
    s = pd.Series([1.0, 2.0, 3.0], name="nav")
    cache.set("test:series", s)
    result = cache.get("test:series")
    assert isinstance(result, pd.Series)
    assert list(result) == [1.0, 2.0, 3.0]
    assert result.name == "nav"


def test_cache_pd_frame():
    """缓存和恢复 pd.DataFrame"""
    cache = _make_cache()
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    cache.set("test:frame", df)
    result = cache.get("test:frame")
    assert isinstance(result, pd.DataFrame)
    assert list(result.columns) == ["a", "b"]


# ── CachedProvider ─────────────────────────────────────

class _MockProvider:
    """模拟 BaseDataProvider"""

    def __init__(self):
        self.call_count = 0

    def name(self):
        return "MockProvider"

    def get_etf_nav(self, symbol):
        self.call_count += 1
        return pd.Series([1.0, 2.0], name=symbol)

    def get_etf_daily(self, symbol, period="1y"):
        self.call_count += 1
        return pd.DataFrame({"close": [10, 11]})

    def get_fund_nav(self, symbol):
        self.call_count += 1
        return pd.Series([1.0, 2.0], name=symbol)

    def get_fund_info(self, symbol):
        self.call_count += 1
        return {"name": symbol, "manager": "Test"}

    def get_fund_holdings(self, symbol):
        self.call_count += 1
        return pd.DataFrame({"stock": ["A", "B"], "weight": [0.5, 0.5]})


def test_cached_provider_reduces_calls():
    """第二次调用相同参数时不走 provider"""
    cache = _make_cache()
    inner = _MockProvider()
    wrapped = CachedProvider(inner, cache)

    # 第一次调用
    r1 = wrapped.get_etf_nav("TEST")
    assert inner.call_count == 1
    assert isinstance(r1, pd.Series)

    # 第二次调用应命中缓存
    r2 = wrapped.get_etf_nav("TEST")
    assert inner.call_count == 1  # 没有增加
    assert list(r2) == [1.0, 2.0]


def test_cached_provider_diff_symbols():
    """不同标的分别缓存"""
    cache = _make_cache()
    inner = _MockProvider()
    wrapped = CachedProvider(inner, cache)

    wrapped.get_etf_nav("A")
    wrapped.get_etf_nav("B")
    assert inner.call_count == 2

    # 再次获取 A — 命中缓存
    wrapped.get_etf_nav("A")
    assert inner.call_count == 2


def test_cached_provider_all_methods():
    """所有代理方法均生效"""
    cache = _make_cache()
    inner = _MockProvider()
    wrapped = CachedProvider(inner, cache)

    for method in ["get_etf_nav", "get_etf_daily", "get_fund_nav",
                   "get_fund_info", "get_fund_holdings"]:
        inner.call_count = 0
        getattr(wrapped, method)("SYM")
        assert inner.call_count == 1, f"{method} 第一次调用"
        getattr(wrapped, method)("SYM")
        assert inner.call_count == 1, f"{method} 应该命中缓存"


def test_cached_provider_name():
    """name() 包含缓存标记"""
    cache = _make_cache()
    wrapped = CachedProvider(_MockProvider(), cache)
    assert "cached" in wrapped.name()
