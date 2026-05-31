/**
 * Renderer for the derivation panel.
 *
 * The backend returns each step as { type, text, latex }. We render the
 * LaTeX via KaTeX when it's available, and fall back to the plain `text`
 * string if KaTeX failed to load (offline, CDN blocked, etc.).
 */

const STEP_TAG_LABEL = {
  equation:     "Equation",
  rearrange:    "Rearrange",
  substitute:   "Substitute",
  result:       "Result",
  intermediate: "Intermediate",
};

/** Render a LaTeX string into `el`, with a plain-text fallback. */
function renderLatex(el, latex, fallbackText) {
  if (window.katex) {
    try {
      window.katex.render(latex, el, { throwOnError: false, displayMode: true });
      return;
    } catch {
      /* fall through to plain text */
    }
  }
  el.textContent = fallbackText;
}

/** Build a single <li> for one derivation step. */
function buildStepNode(step, index) {
  const li = document.createElement("li");
  li.className = `step ${step.type}`;

  const tag = document.createElement("div");
  tag.className = "step-tag";
  tag.textContent = `Step ${index + 1} — ${STEP_TAG_LABEL[step.type] || step.type}`;

  const latex = document.createElement("div");
  latex.className = "latex-render";
  renderLatex(latex, step.latex, step.text);

  li.appendChild(tag);
  li.appendChild(latex);
  return li;
}

/**
 * Render a full solver response into the output panel.
 *
 * @param {Object} dom              { summary, steps, equations, status }
 * @param {Object} result           full payload from POST /api/solve
 */
export function renderResult(dom, result) {
  // ----- result summary -----
  dom.summary.hidden = false;
  dom.summary.innerHTML = "";
  const labelEl = document.createElement("span");
  labelEl.className = "label";
  labelEl.textContent = `${result.target} =`;
  const valueEl = document.createElement("span");
  valueEl.className = "mono";
  valueEl.textContent = `${formatNumber(result.value)} ${result.unit || ""}`.trim();
  dom.summary.appendChild(labelEl);
  dom.summary.appendChild(valueEl);

  // ----- steps -----
  dom.steps.innerHTML = "";
  result.steps.forEach((step, i) => {
    dom.steps.appendChild(buildStepNode(step, i));
  });

  // ----- equations used -----
  if (result.equations_used && result.equations_used.length) {
    dom.equations.hidden = false;
    dom.equations.innerHTML = "Equations used: " +
      result.equations_used.map(n => `<code>${n}</code>`).join(" ");
  } else {
    dom.equations.hidden = true;
  }

  dom.status.textContent = `Solved in ${result.steps.length} step(s).`;
}

/** Show an error message in place of a derivation. */
export function renderError(dom, message) {
  dom.summary.hidden = true;
  dom.equations.hidden = true;
  dom.steps.innerHTML = "";
  dom.status.textContent = "Error";
  return message;
}

/** Friendly number formatting: trim trailing zeros, keep precision. */
function formatNumber(n) {
  if (!Number.isFinite(n)) return String(n);
  // 6 significant digits is plenty for AP-level problems.
  const s = Number(n.toPrecision(6)).toString();
  return s;
}
