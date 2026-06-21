from fastapi import APIRouter
from services.data import get_nav
from services.metrics import nav_percentile, trend_ma, rsi
from db import add_watch, list_watch, del_watch

router = APIRouter()

@router.get("/list")
def get_list(): return list_watch()

@router.post("/add")
def add(code: str): add_watch(code); return {"ok": True}

@router.delete("/del")
def remove(code: str): del_watch(code); return {"ok": True}

@router.get("/signal")
def signal():
    res = []
    for w in list_watch():
        code = w["code"]
        df = get_nav(code)
        if df.empty: continue
        nav = df["nav"]
        pct = nav_percentile(nav)
        year = nav.tail(252)
        dd = float(year.iloc[-1] / year.max() - 1) if len(year) > 0 else 0
        r = rsi(nav)
        tr = trend_ma(nav)

        checks = {
            "估值偏低(分位<35%)": pct < 0.35,
            "已回调(距高点<-10%)": dd < -0.10,
            "未超买(RSI<60)": r < 60,
            "趋势非向下": tr != "向下",
        }
        can_buy = all(checks.values())
        fails = [k for k, v in checks.items() if not v]
        detail = f"分位{pct:.0%} / 距高点{dd:.0%} / RSI{r:.0f} / 趋势{tr}"

        res.append({
            "code": code,
            "can_buy": can_buy,
            "reason": "✅ 满足全部买入条件" if can_buy else "❌ 暂不建议 — " + "、".join(fails),
            "detail": detail,
            "percentile": round(pct, 2), "drawdown": round(dd, 2),
            "rsi": round(r, 0), "trend": tr,
        })
    return res
