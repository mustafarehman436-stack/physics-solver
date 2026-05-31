# Physics 1 Practice Problem Solver & Derivation Engine

An educational tool that solves AP / High-School Physics 1 problems and
**shows its work** — every step of the algebra, not just the final number.

The system is a fully decoupled full-stack app:

| Layer        | Stack                                | Folder       |
|--------------|--------------------------------------|--------------|
| Backend API  | Python · FastAPI · SymPy             | `backend/`   |
| Frontend UI  | Native HTML / CSS / JS · KaTeX       | `frontend/`  |

---

## What it does

You give it a set of **known variables** (with any common unit — mph, ft, lb,
N, J, etc.) and an **unknown target**. The engine:

1. Normalizes every input to base SI and validates dimensional consistency.
2. Picks the equation (or chain of equations) that connects the knowns to
   the target.
3. Algebraically rearranges, substitutes, and evaluates — emitting each
   step in both plain text and LaTeX.
4. Renders the derivation as a step-by-step proof in the browser.

### Equations covered

- Kinematics (1D, constant acceleration):
  `vf = vi + at`, `d = vi·t + ½at²`, `vf² = vi² + 2ad`, `d = ½(vi + vf)t`
- Newton's 2nd law: `F = ma`
- Work: `W = F·d`
- Kinetic energy: `KE = ½mv²`
- Potential energy: `PE = mgh`
- Momentum: `p = mv`

Adding a new equation is one append to `backend/equations.py` — no solver
changes required.

---

## Backend (`backend/`)

```
backend/
├── units.py        # SI normalization + dimensional validation
├── equations.py    # SymPy catalog of AP Physics 1 equations
├── solver.py       # Two-tier symbolic search + step generator
├── app.py          # FastAPI POST /api/solve endpoint
└── requirements.txt
```

Run it:

```bash
cd backend
pip install -r requirements.txt
python app.py        # uvicorn on http://localhost:8000
```

Quick check:

```bash
curl -X POST http://localhost:8000/api/solve \
  -H 'Content-Type: application/json' \
  -d '{
        "knowns": {
          "vi": {"value": 0,   "unit": "m/s"},
          "a":  {"value": 9.8, "unit": "m/s^2"},
          "t":  {"value": 3,   "unit": "s"}
        },
        "target": "d"
      }'
```

Returns the full derivation of `d = 44.1 m`.

---

## Frontend (`frontend/`)

```
frontend/
├── index.html
├── style.css
└── js/
    ├── api.js       # fetch wrapper for /api/solve
    ├── renderer.js  # KaTeX step rendering
    └── app.js       # state, presets, event wiring
```

Run it (any static server works):

```bash
cd frontend
python3 -m http.server 3001
```

Then open <http://localhost:3001>.

The footer shows whether the backend is reachable. Pick a preset
(Free fall, Newton's 2nd, KE, or a chained problem) and click **Solve**.

---

## Architecture notes

- **Decoupled by design.** The backend speaks pure JSON over HTTP; the
  frontend is a static bundle. They can be deployed independently.
- **Symbolic, not numeric.** SymPy rearranges equations algebraically
  before substitution, which is what makes step-by-step derivations
  possible.
- **Dimension safety.** Every variable has a required dimension signature;
  the API rejects nonsense like `F = 10 m/s` before the solver runs.
- **Extensible.** Add an equation by appending to `equations.py` — the
  solver discovers it automatically via free-symbol matching.

---

## License

MIT
