from fastapi import APIRouter, Query
from services.score import screen_4433_by_region, score_fund, classify_region_by_name
from services.direction import get_fund_direction

router = APIRouter()

@router.get("/4433")
def screen(region: str = Query("all", description="all|china|overseas|us|hk|cn")):
    """4433筛选，支持按地区分组。返回包含投资方向标签。"""
    results = screen_4433_by_region(region)
    # Add direction tags to each result
    for r in results:
        code = r.get("基金代码", r.get("code", ""))
        if code:
            r["direction"] = get_fund_direction(str(code))
    return results

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
