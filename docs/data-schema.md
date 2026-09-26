# Quote data format

Each quote is one JSON file in `data/quotes/`, named:

```
<YYYYMMDD>-<uuid>.json
```

The `YYYYMMDD` prefix is the date the quote was *added* to QuoteBook (not
the date the quote was originally said/written) and must match the file's
`added` field. Prepending it lets the sync process and any future tooling
list/fetch quotes in date order without parsing every file first.

## File contents

```json
{
  "id": "7fb0fc9c-1aa0-4b23-a079-a35c49600c84",
  "added": "2026-05-01",
  "date": "47 BC",
  "original_language": "la",
  "translations": {
    "la": "Veni, vidi, vici.",
    "en": "I came, I saw, I conquered."
  },
  "author": {
    "name": "Julius Caesar",
    "link": "https://en.wikipedia.org/wiki/Julius_Caesar"
  },
  "media": {
    "image": "julius_caesar.svg",
    "caption": "Julius Caesar, 1st century BC"
  }
}
```

Field notes:

- `id` — a UUID, unique per quote. Matches the second half of the filename.
- `added` — `YYYY-MM-DD`, must match the filename's date prefix. Used for
  sorting the "View all" list (newest first). Not used to pick "Today's
  Quotes" - see "Quote of the day" in `docs/architecture.md`.
- `date` — a free-form display string used in the "- Author, date" line.
  Doesn't need to be a real date (`"47 BC"`, `"c. 1500"`, etc. are fine).
- `original_language` — an ISO 639 code for the language the quote was
  originally said/written in. Whenever this differs from the reader's
  browser language, the page automatically renders a translation
  underneath the original, no click required, defaulting to English if the
  reader's exact language isn't one of the `translations` (see
  `pickPreferredLanguage` in `src/frontend/js/lang.js`).
- `translations` — a map of language code → text. Must include the original
  language's own text under its own code. All translations are supplied
  up front in the file; the site never calls a translation API.
- `author.name` — required.
- `author.link` — optional. Must start with `http://` or `https://` or the
  file is rejected by the sync process.
- `media` — optional entirely. If present, `caption` is optional (falls
  back to "`<author>, <date>`" in the UI if omitted), and `image` is either:
  - an absolute URL (starts with `http://` or `https://`), used as-is, or
  - otherwise, a filename that must exist in `data/media/`.

Files that fail validation (missing fields, mismatched date prefix, bad
author link, etc.) are skipped and logged during sync — they don't break
the site.
