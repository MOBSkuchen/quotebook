const LANGUAGE_NAME_FALLBACK = {
  la: "Latin",
  grc: "Ancient Greek",
  en: "English",
  de: "German",
  fr: "French",
  es: "Spanish",
  it: "Italian",
  pt: "Portuguese",
  nl: "Dutch",
  ru: "Russian",
  zh: "Chinese",
  ja: "Japanese",
  sa: "Sanskrit",
};

function languageName(code) {
  if (LANGUAGE_NAME_FALLBACK[code]) return LANGUAGE_NAME_FALLBACK[code];
  try {
    const names = new Intl.DisplayNames(["en"], { type: "language" });
    const name = names.of(code);
    if (name && name.toLowerCase() !== code.toLowerCase()) return name;
  } catch (e) {
    // Intl.DisplayNames not supported or code not recognized; fall through.
  }
  return code;
}

// Picks which translation to auto-show under the original: the reader's
// browser language if we have it, else English. Returns null when the
// quote is already in that language (nothing to add) or when neither the
// reader's language nor English is available as a translation.
function pickPreferredLanguage(translations, originalCode) {
  const available = Object.keys(translations);
  const navLang = (navigator.language || "en").slice(0, 2).toLowerCase();

  let target = null;
  if (available.includes(navLang)) target = navLang;
  else if (available.includes("en")) target = "en";

  return target && target !== originalCode ? target : null;
}
