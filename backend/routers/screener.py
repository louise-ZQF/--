from fastapi import APIRouter, Query
from services.score import screen_4433_by_region, score_fund, classify_region_by_name
from services.direction import get_fund_direction

router = APIRouter()


def quick_timing(code: str) -> dict:
    """快速买入时机判断。"""
    from services.data import get_nav
    from services.metrics import nav_percentile, rsi, trend_ma
    df = get_nav(code)
    if df.empty:
        return {"signal": "unknown", "label": "数据不足", "color": "#6b7280"}
    nav = df["nav"]
    pct = nav_percentile(nav)
    r = rsi(nav)
    tr = trend_ma(nav)

    if pct < 0.30 and r < 50 and tr == "向上":
        return {"signal": "buy", "label": "✅ 适合买入", "color": "#10b981",
                "reason": f"低估(分位{pct:.0%})+趋势向上+RSI{r:.0f}未超买"}
    elif pct < 0.30:
        return {"signal": "watch", "label": "👀 关注(低估)", "color": "#f59e0b",
                "reason": f"低估(分位{pct:.0%})但趋势{tr}或RSI{r:.0f}偏高"}
    elif pct > 0.70:
        return {"signal": "wait", "label": "⏳ 估值偏高", "color": "#ef4444",
                "reason": f"估值偏高(分位{pct:.0%})，等回调再买"}
    else:
        return {"signal": "neutral", "label": "🟡 中性", "color": "#f59e0b",
                "reason": f"估值中性(分位{pct:.0%})，可小仓试探"}


@router.get("/4433")
def screen(region: str = Query("all", description="all|china|overseas|us|hk|cn")):
    """4433筛选，支持按地区分组。返回包含投资方向标签。"""
    results = screen_4433_by_region(region)
    for r in results:
        code = str(r.get("基金代码", r.get("code", "")))
        if code:
            r["direction"] = get_fund_direction(code)
    return results


@router.get("/4433-full")
def screen_full(region: str = Query("all"), with_timing: bool = True):
    """完整筛选：4433 + 买入时机 + 方向。"""
    results = screen_4433_by_region(region)
    out = []
    for r in results:
        code = str(r.get("基金代码", r.get("code", "")))
        item = {**r}
        if code:
            item["direction"] = get_fund_direction(code)
            if with_timing:
                item["timing"] = quick_timing(code)
        out.append(item)
    return out

@router.get("/score")
def score(code: str):
    result = score_fund(code)
    result["direction"] = get_fund_direction(code)
    return result

@router.get("/direction")
def direction(code: str):
    """获取基金投资方向标签。"""
    return {
        "code": code,
        "direction": get_fund_direction(code),
        "region": classify_region_by_name("", code) or "unknown",
    }
