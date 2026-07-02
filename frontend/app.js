const statusBox = document.getElementById("status-box");
const refreshBtn = document.getElementById("refresh-btn");
const numbersInput = document.getElementById("numbers-input");
const analyzeBtn = document.getElementById("analyze-btn");
const errorBox = document.getElementById("error-box");
const resultsSection = document.getElementById("results-section");
const generatedTableBody = document.querySelector("#generated-table tbody");
const matchedTableBody = document.querySelector("#matched-table tbody");
const unmatchedNote = document.getElementById("unmatched-note");

function formatDate(iso) {
  if (!iso) return "never";
  const d = new Date(iso);
  return d.toLocaleString();
}

async function loadStatus() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/status`);
    const data = await res.json();
    if (!data.has_data) {
      statusBox.innerHTML = `No historical data stored yet. Click "Refresh data now" to scrape it.`;
      return;
    }
    statusBox.innerHTML = `
      Stored pairs: <strong>${data.pair_count}</strong><br>
      Last scraped: <strong>${formatDate(data.last_scraped)}</strong>
    `;
  } catch (err) {
    statusBox.innerHTML = `Could not reach backend at ${API_BASE_URL}. Is it running?`;
  }
}

refreshBtn.addEventListener("click", async () => {
  refreshBtn.disabled = true;
  refreshBtn.textContent = "Scraping...";
  errorBox.textContent = "";
  try {
    const res = await fetch(`${API_BASE_URL}/api/scrape`, { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Scrape failed.");
    }
    await loadStatus();
  } catch (err) {
    errorBox.textContent = err.message;
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.textContent = "Refresh data now (scrape live site)";
  }
});

function parseNumbers(raw) {
  return raw
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .map((s) => parseInt(s, 10))
    .filter((n) => !Number.isNaN(n));
}

analyzeBtn.addEventListener("click", async () => {
  errorBox.textContent = "";
  const numbers = parseNumbers(numbersInput.value);

  if (numbers.length < 2) {
    errorBox.textContent = "Enter at least 2 numbers.";
    return;
  }

  const mode = document.querySelector('input[name="data-mode"]:checked').value;
  const useFresh = mode === "fresh";

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = useFresh ? "Scraping + analyzing..." : "Analyzing...";

  try {
    const res = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ numbers, use_fresh: useFresh }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Analysis failed.");
    }

    const data = await res.json();
    renderResults(data);
    await loadStatus();
  } catch (err) {
    errorBox.textContent = err.message;
    resultsSection.hidden = true;
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze";
  }
});

function renderResults(data) {
  resultsSection.hidden = false;

  document.getElementById(
    "generated-heading"
  ).textContent = `All generated duplets (${data.generated_pairs.length})`;

  document.getElementById(
    "matched-heading"
  ).textContent = `Matches found in historical data (${data.matched_pairs.length})`;

  generatedTableBody.innerHTML = "";
  data.generated_pairs.forEach(({ pair }) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${pad(pair[0])} - ${pad(pair[1])}</td>`;
    generatedTableBody.appendChild(tr);
  });

  matchedTableBody.innerHTML = "";
  data.matched_pairs.forEach(({ pair, frequency }) => {
    const tr = document.createElement("tr");
    tr.classList.add("highlight");
    tr.innerHTML = `<td>${pad(pair[0])} - ${pad(pair[1])}</td><td>${frequency}</td>`;
    matchedTableBody.appendChild(tr);
  });

  if (data.unmatched_pairs.length > 0) {
    unmatchedNote.textContent =
      `${data.unmatched_pairs.length} pair(s) not found in the top-frequency list ` +
      `(the source site only lists individual pairs that appeared more than ~15 times; ` +
      `lower-frequency pairs aren't identifiable individually from it).`;
  } else {
    unmatchedNote.textContent = "";
  }

  if (data.out_of_range_numbers && data.out_of_range_numbers.length > 0) {
    errorBox.textContent =
      `Note: number(s) ${data.out_of_range_numbers.join(", ")} are outside the 1-50 main number range.`;
  }
}

function pad(n) {
  return n.toString().padStart(2, "0");
}

loadStatus();
