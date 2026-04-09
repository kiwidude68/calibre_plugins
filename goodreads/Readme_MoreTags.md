# Goodreads Plugin — Community Shelf Tags

The Goodreads plugin can optionally fetch additional tags from the community shelves
page of a book (`goodreads.com/book/shelves/{id}`).  Community shelves are user-created
lists that readers use to categorise books — they often cover genres and sub-genres that
are not represented in the curated Goodreads genre list.

This feature is **disabled by default**.  To enable it, open calibre's
*Preferences → Plugins → Metadata sources → Goodreads → Customize* and tick
**"Get additional community shelf tags (makes 1 extra HTTP request)"**.

When enabled, each metadata download makes one additional HTTP request to the shelves
page.  The raw shelf names are filtered by vote count and then converted to calibre tags
using the mapping table described below.

---

## How shelf data is sourced

The plugin first tries to parse shelf data from the Next.js `__NEXT_DATA__` JSON block
embedded in the page (the format used since Goodreads' 2022 redesign).  If that yields
nothing it falls back to legacy HTML parsing of the pre-2022 page structure.  If neither
approach returns data the step is silently skipped and metadata download continues
normally.

---

## Settings

The four settings below are not exposed in the config UI — they are stored directly in
the plugin's JSON config file.  To edit them:

1. Open calibre's configuration directory.  From within calibre go to
   *Preferences → Miscellaneous → Open calibre configuration directory*.
2. Open `plugins/Goodreads.json` in any text editor.
3. Edit the values under the `"Options"` key.
4. Save the file.  Changes take effect immediately for the next download — no restart
   is required.

> **Note:** Opening and saving the plugin's config dialog *preserves* these four keys,
> so it is safe to adjust other settings through the UI after editing the JSON file.

---

### `shelfMappings`

**Type:** object — keys are shelf names (lowercase, hyphen-separated), values are arrays
of calibre tag strings.

Maps a Goodreads community shelf name to one or more calibre tags.  A shelf that does
not appear as a key in this object will never produce a tag, regardless of how many votes
it has.

**Example**

```json
"shelfMappings": {
    "science-fiction": ["Science Fiction"],
    "sci-fi-fantasy":  ["Science Fiction", "Fantasy"],
    "american-history": ["History", "American History"],
    "ya":              ["Young Adult"],
    "young-adult":     ["Young Adult"]
}
```

Shelf names are always lowercase and hyphen-separated exactly as they appear on the
Goodreads shelves page (e.g. `"science-fiction"`, `"young-adult"`).  Each element in the
value array becomes a separate calibre tag.

A comprehensive default mapping is included with the plugin.  You only need to edit this
setting to add shelves that are missing from the defaults, change the calibre tag names,
or remove mappings you do not want.

---

### `shelfThresholdAbsolute`

**Type:** integer  
**Default:** `10`

The minimum number of readers who must have shelved a book under a given shelf name for
it to be considered at all.  Shelves with fewer votes than this value are discarded
before any further processing.

**Example** — keep only shelves with at least 25 votes:

```json
"shelfThresholdAbsolute": 25
```

Raise this value if you find that obscure or noisy shelves are producing unwanted tags.
Set it to `0` or `1` to effectively disable the absolute threshold.

---

### `shelfThresholdPercentage`

**Type:** number (percentage)  
**Default:** `30`

After the absolute threshold has been applied, a second relative threshold is calculated
as a percentage of a reference vote count (see `shelfThresholdPercentageOf` below).
Any shelf whose vote count falls below this percentage of the reference is also discarded.

**Example** — require at least 50 % of the reference count:

```json
"shelfThresholdPercentage": 50
```

A value of `0` disables the percentage threshold entirely.

---

### `shelfThresholdPercentageOf`

**Type:** array of integers (1-based rank positions)  
**Default:** `[3, 4]`

Determines the *reference vote count* used by the percentage threshold.  Each integer
identifies a rank position (where `1` is the shelf with the most votes).  The reference
is the **average** vote count of those ranked shelves.

**Default behaviour** — average of the 3rd- and 4th-ranked shelves:

```json
"shelfThresholdPercentageOf": [3, 4]
```

If a requested rank position does not exist (e.g. the book has fewer than four shelves
after the absolute threshold), that position is simply ignored when calculating the
average.  If no valid positions remain the percentage threshold is skipped.

**Alternative examples**

| Value | Meaning |
|-------|---------|
| `[1]` | Reference is the top shelf alone — very strict relative filtering |
| `[2, 3]` | Reference is the average of the 2nd and 3rd shelves |
| `[5]` | Reference is the 5th-ranked shelf — more permissive filtering |

---

## Threshold worked example

Suppose a book has the following shelves after fetching (sorted by votes, descending):

| Rank | Shelf name       | Votes |
|------|------------------|-------|
| 1    | fiction          | 1200  |
| 2    | fantasy          | 950   |
| 3    | science-fiction  | 400   |
| 4    | adventure        | 350   |
| 5    | classics         | 80    |
| 6    | short-stories    | 8     |

With the default settings (`shelfThresholdAbsolute: 10`, `shelfThresholdPercentage: 30`,
`shelfThresholdPercentageOf: [3, 4]`):

1. **Absolute threshold (≥ 10):** `short-stories` (8 votes) is removed.  Five shelves
   remain.
2. **Reference calculation:** average of rank 3 (`400`) and rank 4 (`350`) = **375**.
3. **Percentage threshold (≥ 30 % of 375 = 112.5):** `classics` (80 votes) is removed.
   Four shelves remain: `fiction`, `fantasy`, `science-fiction`, `adventure`.
4. **Mapping:** only shelf names present in `shelfMappings` produce tags.  If
   `fiction` is not in the mapping it is silently skipped.
