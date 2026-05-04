const state = {
  documents: [],
  selectedDocument: null,
  selectedRuleId: null,
  search: "",
  category: "all",
};

const els = {
  documentNav: document.querySelector("#documentNav"),
  searchInput: document.querySelector("#searchInput"),
  categoryFilter: document.querySelector("#categoryFilter"),
  sectionLabel: document.querySelector("#sectionLabel"),
  documentTitle: document.querySelector("#documentTitle"),
  ruleCount: document.querySelector("#ruleCount"),
  warningCount: document.querySelector("#warningCount"),
  warningPanel: document.querySelector("#warningPanel"),
  ruleList: document.querySelector("#ruleList"),
  detailCategory: document.querySelector("#detailCategory"),
  detailSubject: document.querySelector("#detailSubject"),
  detailOperator: document.querySelector("#detailOperator"),
  detailValue: document.querySelector("#detailValue"),
  detailUnit: document.querySelector("#detailUnit"),
  detailScope: document.querySelector("#detailScope"),
  detailCondition: document.querySelector("#detailCondition"),
  detailException: document.querySelector("#detailException"),
  detailRaw: document.querySelector("#detailRaw"),
};

async function loadData() {
  const response = await fetch("../backend/output/all_rules.json");
  if (!response.ok) {
    throw new Error(`Could not load output JSON: ${response.status}`);
  }
  return response.json();
}

function formatValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (Array.isArray(value)) return value.join(" to ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formatJson(value) {
  if (!value) return "None";
  return JSON.stringify(value, null, 2);
}

function getVisibleRules() {
  const doc = state.selectedDocument;
  if (!doc) return [];

  const query = state.search.trim().toLowerCase();
  return doc.rules.filter((rule) => {
    const matchesCategory = state.category === "all" || rule.category === state.category;
    const haystack = [
      rule.clause,
      rule.category,
      rule.subject,
      rule.operator,
      formatValue(rule.value),
      rule.unit,
      rule.scope,
      rule.raw_text,
    ].join(" ").toLowerCase();
    return matchesCategory && (!query || haystack.includes(query));
  });
}

function renderDocuments() {
  els.documentNav.innerHTML = "";
  state.documents.forEach((doc) => {
    const button = document.createElement("button");
    button.className = `doc-button${doc.source_document === state.selectedDocument?.source_document ? " active" : ""}`;
    button.type = "button";
    button.innerHTML = `
      <strong>${doc.title}</strong>
      <span>${doc.rules.length} rules · ${doc.section}</span>
    `;
    button.addEventListener("click", () => {
      state.selectedDocument = doc;
      state.selectedRuleId = doc.rules[0]?.id || null;
      render();
    });
    els.documentNav.appendChild(button);
  });
}

function renderCategoryFilter() {
  const categories = [...new Set(state.documents.flatMap((doc) => doc.rules.map((rule) => rule.category)))].sort();
  els.categoryFilter.innerHTML = `<option value="all">All categories</option>`;
  categories.forEach((category) => {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category.replaceAll("_", " ");
    els.categoryFilter.appendChild(option);
  });
  els.categoryFilter.value = state.category;
}

function renderSummary() {
  const doc = state.selectedDocument;
  if (!doc) return;

  const warnings = doc.validation?.warnings || [];
  els.sectionLabel.textContent = doc.section;
  els.documentTitle.textContent = doc.title;
  els.ruleCount.textContent = getVisibleRules().length;
  els.warningCount.textContent = warnings.length;

  if (warnings.length) {
    els.warningPanel.hidden = false;
    els.warningPanel.innerHTML = `
      <p>Validation notes</p>
      <ul>${warnings.map((warning) => `<li>${warning}</li>`).join("")}</ul>
    `;
  } else {
    els.warningPanel.hidden = true;
    els.warningPanel.innerHTML = "";
  }
}

function renderRules() {
  const rules = getVisibleRules();
  els.ruleList.innerHTML = "";

  if (!rules.length) {
    els.ruleList.innerHTML = `<div class="empty-state">No rules match the current filters.</div>`;
    clearDetail();
    return;
  }

  if (!rules.some((rule) => rule.id === state.selectedRuleId)) {
    state.selectedRuleId = rules[0].id;
  }

  rules.forEach((rule) => {
    const button = document.createElement("button");
    button.className = `rule-row${rule.id === state.selectedRuleId ? " active" : ""}`;
    button.type = "button";
    button.setAttribute("role", "option");
    button.setAttribute("aria-selected", rule.id === state.selectedRuleId ? "true" : "false");
    button.innerHTML = `
      <span><span class="clause-pill">${rule.clause}</span></span>
      <span>
        <span class="rule-subject">${rule.subject}</span>
        <span class="muted">${rule.category.replaceAll("_", " ")}</span>
      </span>
      <span class="constraint">${rule.operator} ${formatValue(rule.value)} ${rule.unit || ""}</span>
      <span class="muted">${rule.scope || "-"}</span>
    `;
    button.addEventListener("click", () => {
      state.selectedRuleId = rule.id;
      render();
    });
    els.ruleList.appendChild(button);
  });
}

function renderDetail() {
  const selected = getVisibleRules().find((rule) => rule.id === state.selectedRuleId);
  if (!selected) {
    clearDetail();
    return;
  }

  els.detailCategory.textContent = `${selected.category.replaceAll("_", " ")} · clause ${selected.clause}`;
  els.detailSubject.textContent = selected.subject;
  els.detailOperator.textContent = selected.operator || "-";
  els.detailValue.textContent = formatValue(selected.value);
  els.detailUnit.textContent = selected.unit || "-";
  els.detailScope.textContent = selected.scope || "-";
  els.detailCondition.textContent = formatJson(selected.condition);
  els.detailException.textContent = formatJson(selected.exception);
  els.detailRaw.textContent = selected.raw_text || "-";
}

function clearDetail() {
  els.detailCategory.textContent = "Select a rule";
  els.detailSubject.textContent = "No rule selected";
  els.detailOperator.textContent = "-";
  els.detailValue.textContent = "-";
  els.detailUnit.textContent = "-";
  els.detailScope.textContent = "-";
  els.detailCondition.textContent = "None";
  els.detailException.textContent = "None";
  els.detailRaw.textContent = "Select a rule to inspect the source clause.";
}

function render() {
  renderDocuments();
  renderCategoryFilter();
  renderSummary();
  renderRules();
  renderDetail();
}

els.searchInput.addEventListener("input", (event) => {
  state.search = event.target.value;
  render();
});

els.categoryFilter.addEventListener("change", (event) => {
  state.category = event.target.value;
  render();
});

loadData()
  .then((data) => {
    state.documents = data.documents || [];
    state.selectedDocument = state.documents[0] || null;
    state.selectedRuleId = state.selectedDocument?.rules[0]?.id || null;
    render();
  })
  .catch((error) => {
    els.documentTitle.textContent = "Could not load rule output";
    els.sectionLabel.textContent = "Frontend";
    els.ruleList.innerHTML = `<div class="empty-state">${error.message}. Run from the repo root with a local web server.</div>`;
  });
