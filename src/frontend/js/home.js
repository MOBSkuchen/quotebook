document.addEventListener("DOMContentLoaded", async () => {
  const list = document.getElementById("todays-quotes-list");
  const note = document.getElementById("todays-quotes-note");

  try {
    const data = await fetchJSON(`${CONFIG.API_BASE}/api/quotes/today`);

    if (data.is_fallback) {
      note.textContent = `No quotes were added today - showing the most recent additions, from ${data.date}.`;
      note.hidden = false;
    }

    if (data.quotes.length === 0) {
      list.appendChild(el("p", { className: "empty-state", text: "No quotes yet." }));
      return;
    }

    data.quotes.forEach((quote) => list.appendChild(renderQuoteCard(quote)));
  } catch (err) {
    list.appendChild(
      el("p", { className: "error-state", text: "Could not load quotes right now." })
    );
  }
});
