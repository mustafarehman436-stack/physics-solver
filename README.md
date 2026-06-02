# Physics 1 Practice Problem Solver & Derivation Engine

An educational tool that solves AP / High-School Physics 1 problems 
<img width="741" height="759" alt="image" src="https://github.com/user-attachments/assets/afdb7ba6-acb9-45fc-bc03-ec3a197aedb0" />


The system is a fully decoupled full-stack app:

| Layer        | Stack                                | Folder       | Deploy target           |
|--------------|--------------------------------------|--------------|-------------------------|
| Backend API  | Python · FastAPI · SymPy             | `backend/`   | Render (Blueprint)      |
| Frontend UI  | Native HTML / CSS / JS · KaTeX       | `frontend/`  | GitHub Pages (Actions)  |

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

## Deployment

The repo ships with both deploy configs already wired up.

### Backend → Render (free tier)
1. Sign in at <https://render.com> with your GitHub account.
2. **New +** → **Blueprint** → pick this repo.
3. Render reads `render.yaml`, provisions `physics-solver-api`, builds, deploys.
4. Wait until the service shows **Live** (first build is ~3 minutes).

Free instances sleep after ~15 min of inactivity; the first wake takes
30–60 seconds. Subsequent requests are instant.

### Frontend → GitHub Pages
1. Repo **Settings** → **Pages** → *Build and deployment* → **Source: GitHub Actions**.
2. The workflow in `.github/workflows/deploy-frontend.yml` runs on every push
   to `main` that touches `frontend/`. First deploy takes ~1 minute.

### Pointing the frontend at the backend
The frontend auto-detects which backend to use:
- On `localhost` → `http://localhost:8000`
- On `*.github.io` → the Render URL hard-coded in `frontend/js/api.js`

To override at runtime (e.g. preview a different backend without redeploying):
`https://...github.io/physics-solver/?api=https://your-other-host`

The override persists in `localStorage`.

---

## License

MIT
