/**
 * Main controller for the Physics 1 derivation UI.
 *
 * Responsibilities:
 *   - Maintain the list of "known" rows (variable + value + unit).
 *   - Keep the per-variable unit dropdown in sync with the chosen symbol.
 *   - Apply quick presets.
 *   - Translate the UI state into the backend's JSON payload and dispatch
 *     it via the api.js wrapper.
 */

import { solve, ping, API_BASE } from "./api.js";
import { renderResult, renderError } from "./renderer.js";

/* ---------------------------------------------------------------------------
 * Variable metadata — kept in sync with backend/units.py & equations.py.
 * label  : what the user sees in the dropdown
 * units  : allowed unit strings (first entry is the default)
 * ------------------------------------------------------------------------- */
const VAR_META = {
  vi:    { label: "vᵢ  (initial velocity)",    units: ["m/s", "km/h", "mph", "ft/s"] },
  vf:    { label: "vf  (final velocity)",      units: ["m/s", "km/h", "mph", "ft/s"] },
  v:     { label: "v   (velocity)",            units: ["m/s", "km/h", "mph", "ft/s"] },
  a:     { label: "a   (acceleration)",        units: ["m/s^2", "ft/s^2", "g_n"] },
  g:     { label: "g   (gravity)",             units: ["m/s^2", "ft/s^2", "g_n"] },
  t:     { label: "t   (time)",                units: ["s", "ms", "min", "h"] },
  d:     { label: "d   (displacement)",        units: ["m", "km", "cm", "mm", "in", "ft", "mi"] },
  x:     { label: "x   (position)",            units: ["m", "km", "cm", "mm", "in", "ft", "mi"] },
  h:     { label: "h   (height)",              units: ["m", "km", "cm", "mm", "in", "ft"] },
  m:     { label: "m   (mass)",                units: ["kg", "g", "mg", "lb", "slug"] },
  F:     { label: "F   (force)",               units: ["N", "kN", "lbf"] },
  W:     { label: "W   (work)",                units: ["J", "kJ", "cal", "kcal"] },
  KE:    { label: "KE  (kinetic energy)",      units: ["J", "kJ", "cal", "kcal"] },
  PE:    { label: "PE  (potential energy)",    units: ["J", "kJ", "cal", "kcal"] },
  p:     { label: "p   (momentum)",            units: ["kg*m/s"] },
  theta: { label: "θ   (angle)",               units: ["deg", "rad"] },
};
const ALL_VARS = Object.keys(VAR_META);

/* ---------------------------------------------------------------------------
 * Preset problems — each is { knowns, target } in display units.
 * ------------------------------------------------------------------------- */
const PRESETS = {
  free_fall: {
    knowns: [
      { var: "vi", value: 0,   unit: "m/s"   },
      { var: "a",  value: 9.8, unit: "m/s^2" },
      { var: "t",  value: 3,   unit: "s"     },
    ],
    target: "d",
  },
  newton2: {
    knowns: [
      { var: "F", value: 50, unit: "N"  },
      { var: "m", value: 10, unit: "kg" },
    ],
    target: "a",
  },
  ke: {
    knowns: [
      { var: "m", value: 2,  unit: "kg"  },
      { var: "v", value: 30, unit: "mph" },
    ],
    target: "KE",
  },
  chained_vf: {
    knowns: [
      { var: "m",  value: 5,   unit: "kg"  },
      { var: "F",  value: 20,  unit: "N"   },
      { var: "vi", value: 0,   unit: "m/s" },
      { var: "t",  value: 4,   unit: "s"   },
    ],
    target: "vf",
  },
};

/* ---------------------------------------------------------------------------
 * DOM references
 * ------------------------------------------------------------------------- */
const $ = (id) => document.getElementById(id);
const dom = {
  knownsList:  $("knowns-list"),
  addBtn:      $("add-known-btn"),
  presetSel:   $("preset-select"),
  targetSel:   $("target-select"),
  solveBtn:    $("solve-btn"),
  errorBox:    $("error-box"),
  summary:     $("result-summary"),
  steps:       $("steps-list"),
  equations:   $("equations-used"),
  status:      $("status-line"),
  apiStatus:   $("api-status"),
};

/* ---------------------------------------------------------------------------
 * Knowns row builders
 * ------------------------------------------------------------------------- */

function buildVarSelect(initial = "vi") {
  const sel = document.createElement("select");
  for (const v of ALL_VARS) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = VAR_META[v].label;
    sel.appendChild(opt);
  }
  sel.value = initial;
  return sel;
}

function fillUnitSelect(unitSel, varSymbol, preferred) {
  unitSel.innerHTML = "";
  for (const u of VAR_META[varSymbol].units) {
    const opt = document.createElement("option");
    opt.value = u;
    opt.textContent = u;
    unitSel.appendChild(opt);
  }
  unitSel.value = preferred && VAR_META[varSymbol].units.includes(preferred)
    ? preferred
    : VAR_META[varSymbol].units[0];
}

function addKnownRow(prefill = {}) {
  const row = document.createElement("div");
  row.className = "known-row";

  const varSel = buildVarSelect(prefill.var || "vi");

  const valInput = document.createElement("input");
  valInput.type = "number";
  valInput.step = "any";
  valInput.placeholder = "value";
  if (prefill.value !== undefined) valInput.value = prefill.value;

  const unitSel = document.createElement("select");
  fillUnitSelect(unitSel, varSel.value, prefill.unit);

  // When the variable changes, swap the unit options to match its dimension.
  varSel.addEventListener("change", () => fillUnitSelect(unitSel, varSel.value));

  const removeBtn = document.createElement("button");
  removeBtn.className = "remove-btn";
  removeBtn.title = "Remove";
  removeBtn.textContent = "×";
  removeBtn.addEventListener("click", () => row.remove());

  row.appendChild(varSel);
  row.appendChild(valInput);
  row.appendChild(unitSel);
  row.appendChild(removeBtn);

  dom.knownsList.appendChild(row);
  return row;
}

function clearKnowns() {
  dom.knownsList.innerHTML = "";
}

/* ---------------------------------------------------------------------------
 * Target select
 * ------------------------------------------------------------------------- */

function populateTargetSelect(initial = "d") {
  dom.targetSel.innerHTML = "";
  for (const v of ALL_VARS) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = VAR_META[v].label;
    dom.targetSel.appendChild(opt);
  }
  dom.targetSel.value = initial;
}

/* ---------------------------------------------------------------------------
 * Read UI → JSON payload for the backend
 * ------------------------------------------------------------------------- */

function collectPayload() {
  const knowns = {};
  for (const row of dom.knownsList.querySelectorAll(".known-row")) {
    const [varSel, valInput, unitSel] = row.querySelectorAll("select, input");
    const sym = varSel.value;
    const val = parseFloat(valInput.value);
    if (Number.isNaN(val)) {
      throw new Error(`Variable "${sym}" has no numeric value.`);
    }
    if (sym in knowns) {
      throw new Error(`Variable "${sym}" is listed more than once.`);
    }
    knowns[sym] = { value: val, unit: unitSel.value };
  }
  const target = dom.targetSel.value;
  if (target in knowns) {
    throw new Error(`"${target}" is both a known and the target — pick one.`);
  }
  if (Object.keys(knowns).length === 0) {
    throw new Error("Add at least one known variable.");
  }
  return { knowns, target };
}

/* ---------------------------------------------------------------------------
 * Presets
 * ------------------------------------------------------------------------- */

function applyPreset(key) {
  const preset = PRESETS[key];
  if (!preset) return;
  clearKnowns();
  preset.knowns.forEach(addKnownRow);
  populateTargetSelect(preset.target);
}

/* ---------------------------------------------------------------------------
 * Error display
 * ------------------------------------------------------------------------- */

function showError(message) {
  dom.errorBox.hidden = false;
  dom.errorBox.textContent = message;
  renderError(dom, message);
}

function clearError() {
  dom.errorBox.hidden = true;
  dom.errorBox.textContent = "";
}

/* ---------------------------------------------------------------------------
 * Solve handler
 * ------------------------------------------------------------------------- */

async function handleSolve() {
  clearError();
  dom.status.textContent = "Solving…";

  let payload;
  try {
    payload = collectPayload();
  } catch (err) {
    showError(err.message);
    return;
  }

  try {
    const result = await solve(payload);
    renderResult(dom, result);
  } catch (err) {
    showError(err.message);
  }
}

/* ---------------------------------------------------------------------------
 * Boot
 * ------------------------------------------------------------------------- */

function init() {
  dom.apiStatus.textContent = API_BASE;

  // Start with one empty known row and the default preset selected.
  populateTargetSelect("d");
  applyPreset("free_fall");
  dom.presetSel.value = "free_fall";

  dom.addBtn.addEventListener("click", () => addKnownRow());
  dom.solveBtn.addEventListener("click", handleSolve);
  dom.presetSel.addEventListener("change", (e) => {
    if (e.target.value) applyPreset(e.target.value);
  });

  // Surface backend reachability in the footer.
  ping().then((ok) => {
    dom.apiStatus.style.color = ok ? "var(--good)" : "var(--bad)";
    dom.apiStatus.textContent = `${API_BASE}  ${ok ? "● online" : "● offline"}`;
  });
}

document.addEventListener("DOMContentLoaded", init);
