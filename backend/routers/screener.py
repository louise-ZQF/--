import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, Query
from services.score import screen_4433_by_region, score_fund, classify_region_by_name
from services.direction import get_fund_direction
from services.data import get_short_term_perf

logger = logging.getLogger(__name__)
router = APIRouter()


def zhengxi_timing(code: str, fund_name: str = "") -> dict:
    """郑希框架买入时机分析：6维评估 + 明确建议。"""
    from services.data import get_nav
    from services.metrics import nav_percentile, rsi, trend_ma, max_drawdown

    df = get_nav(code)
    if df.empty:
        return {"signal": "unknown", "label": "数据不足", "color": "#6b7280", "analysis": ""}

    nav = df["nav"]
    pct = nav_percentile(nav)
    r = rsi(nav)
    tr = trend_ma(nav)

    ret_1m = float(nav.iloc[-1] / nav.iloc[-22] - 1) if len(nav) >= 22 else 0
    ret_3m = float(nav.iloc[-1] / nav.iloc[-66] - 1) if len(nav) >= 66 else 0
    momentum_ok = ret_1m > 0 or ret_3m > 0.05
    roe_ok = pct < 0.60
    is_qdii = any(kw in (fund_name or "").upper() for kw in ["QDII", "海外", "全球", "纳斯达克", "标普"])
    liquidity_ok = 30 < r < 75
    cycle_ok = tr == "向上" or tr == "未知"
    performance_ok = ret_3m > -0.10

    score = 0
    checks = []
    if momentum_ok:
        score += 25; checks.append({"dim": "景气方向", "ok": True, "detail": f"近1月{ret_1m:.1%}，近3月{ret_3m:.1%}"})
    else:
        checks.append({"dim": "景气方向", "ok": False, "detail": f"近1月{ret_1m:.1%}，近3月{ret_3m:.1%}，动量偏弱"})

    if roe_ok:
        score += 20; checks.append({"dim": "低位弹性", "ok": True, "detail": f"估值分位{pct:.0%}，有修复空间"})
    else:
        checks.append({"dim": "低位弹性", "ok": False, "detail": f"估值分位{pct:.0%}，已在高位"})

    if is_qdii:
        score += 15; checks.append({"dim": "全球视野", "ok": True, "detail": "QDII/海外基金"})
    else:
        score += 8; checks.append({"dim": "全球视野", "ok": False, "detail": "纯A股基金"})

    if liquidity_ok:
        score += 10; checks.append({"dim": "流动性", "ok": True, "detail": f"RSI={r:.0f}，流动性适中"})
    else:
        checks.append({"dim": "流动性", "ok": False, "detail": f"RSI={r:.0f}，{'过热' if r >= 75 else '过低'}"})

    if cycle_ok:
        score += 15; checks.append({"dim": "周期拼接", "ok": True, "detail": f"趋势{tr}"})
    else:
        checks.append({"dim": "周期拼接", "ok": False, "detail": f"趋势{tr}，不宜介入"})

    if performance_ok:
        score += 15; checks.append({"dim": "业绩印证", "ok": True, "detail": f"近3月{ret_3m:.1%}"})
    else:
        checks.append({"dim": "业绩印证", "ok": False, "detail": f"近3月{ret_3m:.1%}，业绩走弱"})

    if score >= 75:
        signal, label, color = "buy", "强烈推荐买入", "#10b981"
        advice = "郑希框架6维评估优秀，当前是较好买入时机。建议分批建仓，优先关注景气方向。"
    elif score >= 55:
        signal, label, color = "cautious_buy", "可考虑买入", "#f59e0b"
        advice = "部分维度偏弱，可小仓试探或等回调加仓。关注未达标维度的改善。"
    elif score >= 35:
        signal, label, color = "wait", "建议观望", "#f59e0b"
        advice = "多项指标偏弱，建议等估值回落或趋势改善后再考虑。"
    else:
        signal, label, color = "avoid", "暂不建议", "#ef4444"
        advice = "当前不满足郑希框架的买入标准。关注趋势反转信号。"

    return {
        "signal": signal, "label": label, "color": color,
        "score": score, "max_score": 100,
        "advice": advice,
        "checks": checks,
        "summary": f"郑希6维评分: {score}/100 · {label}",
    }


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
    """完整筛选：4433 + 买入时机 + 方向。并行处理（max_workers=5）。"""
    results = screen_4433_by_region(region)

    def process_one(r):
        code = str(r.get("基金代码", r.get("code", "")))
        name = str(r.get("基金简称", r.get("name", "")))
        item = {**r}
        if not code:
            item["error"] = "无基金代码"
            return item
        try: item["direction"] = get_fund_direction(code)
        except Exception: item["direction"] = []
        try: item["perf"] = get_short_term_perf(code)
        except Exception: item["perf"] = {}
        if with_timing:
            try: item["timing"] = zhengxi_timing(code, name)
            except Exception: item["timing"] = {"signal": "unknown", "label": "分析异常", "color": "#6b7280", "analysis": ""}
        return item

    out = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_one, r): i for i, r in enumerate(results)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                out.append((idx, future.result()))
            except Exception as exc:
                r = results[idx]
                code = str(r.get("基金代码", r.get("code", "")))
                out.append((idx, {**r, "code": code, "direction": [], "perf": {}, "error": str(exc)}))

    out.sort(key=lambda x: x[0])
    return [item for _, item in out]


@router.get("/score")
def score(code: str):
    from services.data import get_fund_overview, get_fund_manager_info, get_fund_risk_data
    result = score_fund(code)
    result["direction"] = get_fund_direction(code)
    result["overview"] = get_fund_overview(code)
    result["manager"] = get_fund_manager_info(code)
    result["risk"] = get_fund_risk_data(code)
    return result


@router.get("/direction")
def direction(code: str):
    """获取基金投资方向标签。"""
    return {
        "code": code,
        "direction": get_fund_direction(code),
        "region": classify_region_by_name("", code) or "unknown",
    }
