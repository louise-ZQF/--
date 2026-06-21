from fastapi import APIRouter, Query
from services.score import screen_4433_by_region, score_fund, get_fund_direction

router = APIRouter()

@router.get("/4433")
def screen(region: str = Query("all", description="all|china|overseas|us|hk|cn")):
    """4433筛选，支持按地区分组。
    - china: A股+港股
    - overseas: 海外(QDII/美股/日韩)
    - us: 美股为主
    - cn: A股为主
    - hk: 港股为主
    - all: 全部
    """
    return screen_4433_by_region(region)

@router.get("/score")
def score(code: str):
    result = score_fund(code)
    result["direction"] = get_fund_direction(code)
    return result

@router.get("/direction")
def direction(code: str):
    """获取基金投资方向标签。"""
    from services.data import classify_region
    return {
        "code": code,
        "direction": get_fund_direction(code),
        "region": classify_region(code),
    }
