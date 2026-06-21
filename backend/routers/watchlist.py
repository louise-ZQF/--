from fastapi import APIRouter
from services.data import get_nav, get_all_funds
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
    # Get name map
    try:
        all_funds = get_all_funds()
        name_map = {}
        for _, row in all_funds.iterrows():
            name_map[str(row.get("基金代码", ""))] = str(row.get("基金简称", ""))
    except Exception:
        name_map = {}

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
        name = name_map.get(code, code)

        # Detailed buy analysis
        checks = {}
        checks["估值偏低(分位<35%)"] = {"pass": pct < 0.35, "value": f"当前分位{pct:.0%}"}
        checks["已回调(距高点<-10%)"] = {"pass": dd < -0.10, "value": f"距年内高点{dd:.0%}"}
        checks["未超买(RSI<60)"] = {"pass": r < 60, "value": f"RSI={r:.0f}"}
        checks["趋势非向下"] = {"pass": tr != "向下", "value": f"趋势{tr}"}

        can_buy = all(c["pass"] for c in checks.values())

        # Build detailed reason
        if can_buy:
            reason_text = "✅ 四维条件全部满足，可以考虑分批买入"
        else:
            failed = [k for k, v in checks.items() if not v["pass"]]
            reason_text = f"❌ {len(failed)}项条件未满足："
            for f_item in failed:
                reason_text += f"\n  · {f_item}（{checks[f_item]['value']}）"

        res.append({
            "code": code, "name": name,
            "can_buy": can_buy,
            "reason": reason_text,
            "detail": f"估值分位{pct:.0%} · 距高点{dd:.0%} · RSI{r:.0f} · 趋势{tr}",
            "checks": {k: {"pass": v["pass"], "value": v["value"]} for k, v in checks.items()},
            "percentile": round(pct, 2), "drawdown": round(dd, 2),
            "rsi": round(r, 0), "trend": tr,
        })
    return res
