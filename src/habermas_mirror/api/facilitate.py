"""Facilitator pipeline HTTP endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from habermas_mirror.facilitator import facilitate
from habermas_mirror.models import StatementOut

router = APIRouter()


class FacilitateOut(BaseModel):
    session_id: str
    stages: list[StatementOut]


@router.post(
    "/sessions/{session_id}/facilitate",
    response_model=FacilitateOut,
    status_code=201,
)
def run_facilitate(session_id: str) -> FacilitateOut:
    try:
        results = facilitate(session_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    return FacilitateOut(session_id=session_id, stages=results)
