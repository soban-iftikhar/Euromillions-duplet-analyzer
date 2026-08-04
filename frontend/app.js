const statusLine = document.getElementById("status-line");
const numbersInput = document.getElementById("numbers-input");
const ballPreview = document.getElementById("ball-preview");
const analyzeBtn = document.getElementById("analyze-btn");
const errorBox = document.getElementById("error-box");
const receiptSection = document.getElementById("receipt");
const receiptSummary = document.getElementById("receipt-summary");
const receiptList = document.getElementById("receipt-list");
const receiptFootnote = document.getElementById("receipt-footnote");
const receiptPlaceholder = document.getElementById("receipt-placeholder");

function pad(n) {
  return n.toString().padStart(2, "0");
}

function formatDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

async function loadStatus() {
  try {
    const res = await fetch(`${API_BASE_URL}/api/status`);
    const data = await res.json();
    if (!data.has_data) {
      statusLine.innerHTML = `No historical data on file yet.`;
      return;
    }
    statusLine.innerHTML = `<strong>${data.pair_count}</strong> pairs on file &middot; updated ${formatDate(data.last_scraped)}`;
  } catch (err) {
    statusLine.innerHTML = `Couldn't reach the data service. Try again shortly.`;
  }
}

function parseNumbers(raw) {
  return raw
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .map((s) => parseInt(s, 10))
    .filter((n) => !Number.isNaN(n));
}

function renderBallPreview() {
  const numbers = parseNumbers(numbersInput.value);
  ballPreview.innerHTML = "";
  numbers.forEach((n) => {
    const ball = document.createElement("div");
    ball.className = "ball";
    ball.textContent = pad(n);
    ballPreview.appendChild(ball);
  });
}

numbersInput.addEventListener("input", renderBallPreview);

analyzeBtn.addEventListener("click", async () => {
  errorBox.textContent = "";
  const numbers = parseNumbers(numbersInput.value);

  if (numbers.length < 2) {
    errorBox.textContent = "Enter at least 2 numbers.";
    return;
  }

  analyzeBtn.disabled = true;
  analyzeBtn.querySelector("span").textContent = "🎲 Checking...";

  try {
    const res = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ numbers, use_fresh: false }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Couldn't check those numbers.");
    }

    const data = await res.json();
    renderResults(data);
  } catch (err) {
    errorBox.textContent = err.message;
    receiptSection.hidden = true;
    receiptPlaceholder.hidden = false;
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.querySelector("span").textContent = "🎲 Check pairs";
  }
});

function renderResults(data) {
  receiptPlaceholder.hidden = true;

  // restart the print-in animation on every run
  receiptSection.hidden = true;
  void receiptSection.offsetWidth;
  receiptSection.hidden = false;

  const matchedLookup = new Map();
  data.matched_pairs.forEach((m) => matchedLookup.set(`${m.pair[0]}-${m.pair[1]}`, m.frequency));

  receiptSummary.innerHTML =
    `<strong>${data.matched_pairs.length}</strong> of <strong>${data.generated_pairs.length}</strong> pairs found in historical data`;

  receiptList.innerHTML = "";
  data.generated_pairs.forEach(({ pair }) => {
    const key = `${pair[0]}-${pair[1]}`;
    const freq = matchedLookup.get(key);
    const isMatch = freq !== undefined;

    const row = document.createElement("div");
    row.className = `receipt-row ${isMatch ? "matched" : "unmatched"}`;
    row.innerHTML = `
      <div class="pair-balls">
        <div class="ball">${pad(pair[0])}</div>
        <span class="pair-sep">&middot;</span>
        <div class="ball">${pad(pair[1])}</div>
      </div>
      <div class="leader"></div>
      <div class="count">${isMatch ? freq + "&times;" : "&mdash;"}</div>
    `;
    receiptList.appendChild(row);
  });

  const notes = [];
  if (data.unmatched_pairs.length > 0) {
    notes.push(
      `"&mdash;" means the pair isn't in the source site's top-frequency list (it only lists pairs drawn more than ~15 times) &mdash; not that it never occurred.`
    );
  }
  if (data.out_of_range_numbers && data.out_of_range_numbers.length > 0) {
    notes.push(`Number(s) ${data.out_of_range_numbers.join(", ")} are outside the 1&ndash;50 main number range.`);
  }
  receiptFootnote.innerHTML = notes.join(" ");
  receiptFootnote.hidden = notes.length === 0;
}

loadStatus();
