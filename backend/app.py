"""
FastAPI server for the Physics 1 derivation engine.

POST /api/solve  →  step-by-step algebraic derivation in JSON.

Request body
------------
{
  "knowns": {
    "vi": {"value": 0,   "unit": "m/s"},
    "a":  {"value": 9.8, "unit": "m/s^2"},
    "t":  {"value": 3,   "unit": "s"}
  },
  "target": "d"
}

Response body
-------------
{
  "target": "d",
  "value":  44.1,
  "unit":   "m",
  "steps":  [ {"type": "...", "text": "...", "latex": "..."}, ... ],
  "equations_used": ["kin_d_t"]
}
"""

from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from solver import SolverError, solve
from units import UnitError, normalize_payload

app = FastAPI(title="Physics 1 Derivation API", version="1.0.0")

# Open CORS — the frontend is a static page served from anywhere.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class QuantityIn(BaseModel):
    value: float
    unit: str = Field(..., description="Unit string, e.g. 'mph', 'm/s^2'")


class SolveRequest(BaseModel):
    knowns: Dict[str, QuantityIn]
    target: str = Field(..., description="Symbol of the unknown, e.g. 'd'")


class StepOut(BaseModel):
    type: str
    text: str
    latex: str


class SolveResponse(BaseModel):
    target: str
    value: float
    unit: str
    steps: List[StepOut]
    equations_used: List[str]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> Dict[str, str]:
    """Lightweight liveness probe."""
    return {"status": "ok"}


@app.post("/api/solve", response_model=SolveResponse)
def api_solve(req: SolveRequest) -> SolveResponse:
    """
    Pipeline: validate & normalize units → symbolic solve → return
    the full derivation log.
    """
    # 1) Normalize the incoming payload to SI, validating dimensions.
    try:
        raw = {k: q.model_dump() for k, q in req.knowns.items()}
        si_knowns = normalize_payload(raw)
    except UnitError as err:
        raise HTTPException(status_code=400, detail=f"Unit error: {err}")

    # 2) Run the symbolic engine.
    try:
        result = solve(si_knowns, req.target)
    except SolverError as err:
        raise HTTPException(status_code=422, detail=f"Solver error: {err}")

    return SolveResponse(**result)


# Allow `python app.py` for quick local dev.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
