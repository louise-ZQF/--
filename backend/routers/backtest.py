from fastapi import APIRouter
from pydantic import BaseModel
from services.backtest import dca_backtest

router = APIRouter()

class DCAReq(BaseModel):
    code: str
    amount: float = 1000
    freq: str = "W"

@router.post("/dca")
def dca(req: DCAReq):
    return dca_backtest(req.code, req.amount, req.freq)
