document.addEventListener("DOMContentLoaded", async () => {
  const list = document.getElementById("todays-quotes-list");

  try {
    const data = await fetchJSON(`${CONFIG.API_BASE}/api/quotes/today`);

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
