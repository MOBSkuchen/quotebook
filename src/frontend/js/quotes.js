async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

function el(tag, opts = {}) {
  const node = document.createElement(tag);
  if (opts.className) node.className = opts.className;
  if (opts.text !== undefined) node.textContent = opts.text;
  if (opts.attrs) {
    for (const [key, value] of Object.entries(opts.attrs)) {
      node.setAttribute(key, value);
    }
  }
  return node;
}

const SAFE_URL_RE = /^https?:\/\//i;

function renderMediaCaption(captionText) {
  const wrap = el("p", { className: "quote-media-caption" });
  const commaIndex = captionText.indexOf(",");
  if (commaIndex === -1) {
    wrap.appendChild(el("span", { className: "caption-line", text: captionText }));
    return wrap;
  }
  const line1 = captionText.slice(0, commaIndex).trim();
  const line2 = captionText.slice(commaIndex + 1).trim();
  wrap.appendChild(el("span", { className: "caption-line", text: line1 }));
  wrap.appendChild(el("span", { className: "caption-line", text: line2 }));
  return wrap;
}

function renderQuoteCard(quote) {
  const card = el("article", { className: "quote-card" });
  const main = el("div", { className: "quote-main" });
  const body = el("div", { className: "quote-body" });

  let currentLang = quote.original_language;
  const textEl = el("blockquote", {
    className: "quote-text",
    text: quote.translations[currentLang],
  });
  textEl.lang = currentLang;
  body.appendChild(textEl);

  // Auto-translate into the reader's language whenever the quote isn't
  // already in it, defaulting to English when their language isn't
  // available as a translation.
  const autoTarget = pickPreferredLanguage(quote.translations, quote.original_language);
  let autoEl = null;
  if (autoTarget) {
    autoEl = el("p", {
      className: "quote-auto-translation",
      text: quote.translations[autoTarget],
    });
    autoEl.lang = autoTarget;
    body.appendChild(autoEl);
  }

  const attribution = el("p", { className: "quote-attribution" });
  attribution.appendChild(document.createTextNode("- "));
  if (quote.author.link && SAFE_URL_RE.test(quote.author.link)) {
    attribution.appendChild(
      el("a", {
        text: quote.author.name,
        attrs: {
          href: quote.author.link,
          target: "_blank",
          rel: "noopener noreferrer",
        },
      })
    );
  } else {
    attribution.appendChild(document.createTextNode(quote.author.name));
  }
  if (quote.date) {
    attribution.appendChild(document.createTextNode(`, ${quote.date}`));
  }
  body.appendChild(attribution);

  main.appendChild(body);

  if (quote.media && quote.media.url) {
    const mediaWrap = el("div", { className: "quote-media" });
    mediaWrap.appendChild(
      el("img", {
        attrs: {
          src: quote.media.url,
          alt: `Portrait of ${quote.author.name}`,
          loading: "lazy",
        },
      })
    );
    const caption =
      quote.media.caption ||
      `${quote.author.name}${quote.date ? ", " + quote.date : ""}`;
    mediaWrap.appendChild(renderMediaCaption(caption));
    main.appendChild(mediaWrap);
  }

  card.appendChild(main);

  // Kept at the very bottom of the card, spanning its full width, rather
  // than tucked under the quote text.
  const langCodes = Object.keys(quote.translations);
  if (langCodes.length > 1) {
    const btnRow = el("div", { className: "quote-lang-buttons" });
    btnRow.appendChild(
      el("span", { className: "quote-lang-label", text: "View in:" })
    );
    langCodes.forEach((code) => {
      const btn = el("button", {
        className: "quote-lang-btn",
        text: languageName(code),
      });
      btn.type = "button";
      btn.dataset.lang = code;
      if (code === currentLang) btn.classList.add("active");
      btn.addEventListener("click", () => {
        currentLang = code;
        textEl.textContent = quote.translations[code];
        textEl.lang = code;
        btnRow.querySelectorAll(".quote-lang-btn").forEach((b) => {
          b.classList.toggle("active", b.dataset.lang === code);
        });
        // Hide the auto-translation once it would just repeat what's now
        // shown as the primary text.
        if (autoEl) autoEl.hidden = code === autoTarget;
      });
      btnRow.appendChild(btn);
    });
    card.appendChild(btnRow);
  }

  return card;
}
