"""简单内存缓存，避免反复抓 akshare"""
import time, functools

_store = {}
def cached(ttl=3600):
    def deco(fn):
        @functools.wraps(fn)
        def wrap(*a, **k):
            key = (fn.__name__, a, tuple(sorted(k.items())))
            now = time.time()
            if key in _store and now - _store[key][0] < ttl:
                return _store[key][1]
            val = fn(*a, **k)
            _store[key] = (now, val)
            return val
        return wrap
    return deco
