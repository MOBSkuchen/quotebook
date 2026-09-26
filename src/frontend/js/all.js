const PAGE_SIZE = 20;
let searchDebounce = null;

document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("search-input");
  const params = new URLSearchParams(window.location.search);
  const initialQuery = params.get("q") || "";
  searchInput.value = initialQuery;

  loadQuotes(initialQuery, 1);

  searchInput.addEventListener("input", () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      const q = searchInput.value.trim();
      const url = new URL(window.location);
      if (q) {
        url.searchParams.set("q", q);
      } else {
        url.searchParams.delete("q");
      }
      history.replaceState({}, "", url);
      loadQuotes(q, 1);
    }, 300);
  });
});

async function loadQuotes(q, page) {
  const list = document.getElementById("quotes-list");
  const pagination = document.getElementById("pagination");
  list.textContent = "";
  pagination.textContent = "";
  list.appendChild(el("p", { className: "loading-state", text: "Loading…" }));

  try {
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    qs.set("page", String(page));
    qs.set("page_size", String(PAGE_SIZE));

    const data = await fetchJSON(`${CONFIG.API_BASE}/api/quotes?${qs.toString()}`);
    list.textContent = "";

    if (data.quotes.length === 0) {
      const message = q ? `No quotes match "${q}".` : "No quotes yet.";
      list.appendChild(el("p", { className: "empty-state", text: message }));
      return;
    }

    data.quotes.forEach((quote) => list.appendChild(renderQuoteCard(quote)));
    renderPagination(data.total, page, q);
  } catch (err) {
    list.textContent = "";
    list.appendChild(
      el("p", { className: "error-state", text: "Could not load quotes right now." })
    );
  }
}

function renderPagination(total, page, q) {
  const nav = document.getElementById("pagination");
  nav.textContent = "";
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (totalPages <= 1) return;

  const prev = el("button", { text: "Previous" });
  prev.type = "button";
  prev.disabled = page <= 1;
  prev.addEventListener("click", () => loadQuotes(q, page - 1));

  const next = el("button", { text: "Next" });
  next.type = "button";
  next.disabled = page >= totalPages;
  next.addEventListener("click", () => loadQuotes(q, page + 1));

  const info = el("span", {
    className: "pagination-info",
    text: `Page ${page} of ${totalPages}`,
  });

  nav.appendChild(prev);
  nav.appendChild(info);
  nav.appendChild(next);
}
