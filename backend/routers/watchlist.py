import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter
from services.data import get_nav, get_all_funds, get_fund_overview, get_fund_manager_info, get_fund_risk_data, get_short_term_perf, get_full_holdings
from services.metrics import nav_percentile, trend_ma, rsi
from services.evaluate import evaluate_fund
from db import add_watch, list_watch, del_watch

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/list")
def get_list(): return list_watch()


@router.post("/add")
def add(code: str): add_watch(code); return {"ok": True}


@router.delete("/del")
def remove(code: str): del_watch(code); return {"ok": True}


@router.get("/holdings")
def fund_holdings(code: str):
    """获取基金的完整持仓和地域分布。"""
    return get_full_holdings(code)


@router.get("/signal")
def signal():
    """分析自选基金的买入信号。

    每只基金通过 ThreadPoolExecutor 并行处理（max_workers=5），
    单只基金的网络请求失败不会导致整体崩溃。
    """
    from services.snapshot import get_snapshot, set_snapshot

    cache_key = "watchlist:signal"
    cached = get_snapshot(cache_key)
    if cached is not None:
        return cached

    try:
        all_funds = get_all_funds()
        name_map = {}
        for _, row in all_funds.iterrows():
            name_map[str(row.get("基金代码", ""))] = str(row.get("基金简称", ""))
    except Exception:
        name_map = {}

    watchlist = list_watch()

    def process_one(w):
        code = w["code"]
        try:
            df = get_nav(code)
        except Exception:
            df = None

        if df is None or df.empty:
            return {
                "code": code,
                "name": name_map.get(code, code),
                "error": "无净值数据",
            }

        nav = df["nav"]
        pct = nav_percentile(nav)
        year = nav.tail(252)
        dd = float(year.iloc[-1] / year.max() - 1) if len(year) > 0 else 0
        r = rsi(nav)
        tr = trend_ma(nav)
        name = name_map.get(code, code)

        checks = {}
        checks["估值偏低(分位<35%)"] = {"pass": pct < 0.35, "value": f"当前分位{pct:.0%}"}
        checks["已回调(距高点<-10%)"] = {"pass": dd < -0.10, "value": f"距年内高点{dd:.0%}"}
        checks["未超买(RSI<60)"] = {"pass": r < 60, "value": f"RSI={r:.0f}"}
        checks["趋势非向下"] = {"pass": tr != "向下", "value": f"趋势{tr}"}

        can_buy = all(c["pass"] for c in checks.values())

        if can_buy:
            reason_text = "四维条件全部满足，可以考虑分批买入"
        else:
            failed = [k for k, v in checks.items() if not v["pass"]]
            reason_text = f"{len(failed)}项条件未满足："
            for f_item in failed:
                reason_text += f"\n  · {f_item}（{checks[f_item]['value']}）"

        try: overview = get_fund_overview(code)
        except Exception: overview = {}
        try: manager = get_fund_manager_info(code)
        except Exception: manager = {}
        try: risk = get_fund_risk_data(code)
        except Exception: risk = {}
        try: perf = get_short_term_perf(code)
        except Exception: perf = {}
        try: holdings_summary = _build_holdings_summary(code)
        except Exception: holdings_summary = {}
        try: evaluation = evaluate_fund(code, name)
        except Exception: evaluation = {}

        return {
            "code": code, "name": name, "can_buy": can_buy,
            "reason": reason_text,
            "detail": f"估值分位{pct:.0%} · 距高点{dd:.0%} · RSI{r:.0f} · 趋势{tr}",
            "checks": {k: {"pass": v["pass"], "value": v["value"]} for k, v in checks.items()},
            "percentile": round(pct, 2), "drawdown": round(dd, 2),
            "rsi": round(r, 0), "trend": tr,
            "overview": overview, "manager": manager, "risk": risk,
            "perf": perf, "holdings_summary": holdings_summary, "evaluation": evaluation,
        }

    res = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_one, w): w for w in watchlist}
        for future in as_completed(futures):
            w = futures[future]
            try:
                res.append(future.result())
            except Exception as exc:
                res.append({
                    "code": w["code"],
                    "name": name_map.get(w["code"], w["code"]),
                    "error": str(exc),
                })

    code_order = {w["code"]: i for i, w in enumerate(watchlist)}
    res.sort(key=lambda o: code_order.get(o["code"], 999))
    res.sort(key=lambda o: (o.get("code", "999999")))
    set_snapshot(cache_key, res)
    return res


def _build_holdings_summary(code: str) -> dict:
    """构建持仓摘要：前5大持仓 + 地域分布。"""
    try:
        data = get_full_holdings(code)
        holdings = data.get("持仓", [])
        top5 = holdings[:5]
        region = data.get("地域分布", {})
        return {
            "前5持仓": top5,
            "地域分布": region,
            "总占比": data.get("总占比", 0),
            "季度": data.get("季度", ""),
        }
    except Exception:
        return {"前5持仓": [], "地域分布": {}, "总占比": 0, "季度": ""}
