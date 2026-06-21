from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from services.optimize import optimize

router = APIRouter()

class OptReq(BaseModel):
    codes: List[str]
    method: str = "max_sharpe"

@router.post("/optimize")
def do_opt(req: OptReq):
    return optimize(req.codes, req.method)
