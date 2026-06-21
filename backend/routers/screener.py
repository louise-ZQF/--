from fastapi import APIRouter
from services.score import screen_4433, score_fund

router = APIRouter()

@router.get("/4433")
def screen(): return screen_4433()

@router.get("/score")
def score(code: str): return score_fund(code)
