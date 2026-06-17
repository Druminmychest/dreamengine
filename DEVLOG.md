# DEVLOG — Rocky's Dream Engine
*Maintained by: Rob Roach (robertdroach)*
*Last updated: June 5, 2026*

---

## Project Summary

An art project / web application combining the I Ching oracle structure with surrealist exquisite corpse poetry generation. Users submit phrases anonymously, a human curator assigns them to one of 64 I Ching hexagrams, and the system generates a poem drawn from the dream pool when a user submits a new phrase.

The project is a deliberate collaboration between human unconscious (phrase contributions) and AI assembly — the AI is a co-creator, not a tool.

Rocky is the presiding intelligence of the project — named for Rob's closest friend, a father figure who died during Covid. The project is a tribute: an attempt to crystallize and pass forward the texture of a particular human soul.

---

## Core Concept

- 64 I Ching hexagrams act as organizational buckets for submitted phrases
- User submits a phrase → system runs an I Ching consultation algorithmically → identifies a hexagram → draws N phrases randomly from that hexagram's pool → assembles exquisite corpse poem → returns poem to user alongside traditional hexagram text
- A human curator (Rob) reviews all submitted phrases before they enter the dream pool, assigning each to a hexagram intuitively
- The curation step is intentional — the curator's unconscious shapes the pool

---

## Current Status (as of June 5, 2026)

**LIVE and deployed at: https://dreamengine.lightclub.cloud**

### What is working:
- Public submission interface (mobile-first, dark palette with gold accents)
- I Ching consultation algorithm
- Exquisite corpse poem generator drawing from PostgreSQL dream pool
- Poem + hexagram text returned to user as oracle reading
- "Distill into Poetry" button — reshapes poem via Anthropic API
- Protected admin curation interface at `/admin/phrases`
- Mobile curation interface at `/admin/mobile`
- Rocky's Time Machine at `/time-machine` — four temporal windows, daily caching
- Rocky's humours navigation — persistent fixed bar across all pages
- Coming-soon pages for Rocky Reasoning (`/coming-soon/reasoning`) and Rocky Listening (`/coming-soon/listening`)
- About page at `/about` — explains Dream Engine, Time Machine, and humours selector
- PostgreSQL database on Render (Ohio region)
- GitHub repo: https://github.com/Druminmychest/dreamengine

### Database state:
- 500+ approved phrases in the dream pool
- `time_machine_cache` table added — stores daily Time Machine narratives per era

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Backend | Python / Flask |
| Database | PostgreSQL (Render managed) |
| Server | Gunicorn |
| Hosting | Render (free tier) |
| Version control | GitHub (Druminmychest/dreamengine) |
| Frontend | HTML/CSS templates, mobile-first |
| AI | Anthropic API (claude-sonnet-4-6) |

### Key files:
- `app.py` — main Flask application, all routes
- `templates/index.html` — public submission interface
- `templates/result.html` — oracle/poem output page
- `templates/time_machine.html` — Rocky's Time Machine
- `templates/about.html` — project description
- `templates/coming_soon.html` — placeholder for future lobes
- `requirements.txt` — Flask, gunicorn, psycopg2, anthropic
- `Procfile` — `web: gunicorn app:app`

### Environment variables (set in Render dashboard, NOT in code):
- `DATABASE_URL` — PostgreSQL connection string
- `ADMIN_USERNAME` — admin login
- `ADMIN_PASSWORD` — admin password
- `ANTHROPIC_API_KEY` — Anthropic API key

---

## Rocky's Architecture — The Four Humours

Rocky is not a single app. Rocky is a presence with four distinct modes of consciousness, navigable via a persistent fixed bar of colored dots at the top of every page. The concept draws on Aristotle's four aspects of the human soul.

| Lobe | Color | Status | Description |
|------|-------|--------|-------------|
| Dream Engine | Gold #C9A84C | Live | Surrealist oracle. Rocky dreaming through collective human expression. |
| Time Machine | Teal #5DCAA5 | Live | Daily historical narratives. Rocky remembering, witnessing the sweep of history. |
| Rocky Reasoning | Blue #85B7EB | Coming soon | Rocky thinking through a problem. Straight-talking, no-nonsense wisdom. |
| Rocky Listening | Purple #AFA9EC | Coming soon | Rocky as confessor, sounding board, old friend in the chair across from you. |

The nav dots are persistent and fixed at the top of every page. Active lobe is full opacity; available lobes are dimmed; coming-soon lobes are nearly invisible. Hover tooltips show lobe names on desktop.

---

## Architecture Decisions (and why)

**SQLite → PostgreSQL:** Migrated during deployment. SQLite fine for local dev; PostgreSQL needed for hosted environment and future scale.

**Single file app.py:** Intentional for PoC simplicity. Will need reorganization before scaling.

**Anonymous contributions:** No accounts, no identifying information. Contributor token only.

**Human curation layer:** All phrases pass through Rob's intuitive hexagram assignment before entering the pool. This is a feature, not a bottleneck — it's where the artistic intelligence lives.

**Mobile-first web (not native app):** Lower barrier, no app store, easier to iterate.

**Time Machine — daily caching:** API calls are made once per era per day and cached in PostgreSQL. Subsequent loads serve from cache instantly. Rocky speaks once a day — this is intentional, not a limitation.

---

## Known Limitations / Technical Debt

- **Render free tier spin-down:** First load after 15 minutes of inactivity takes 30–60 seconds.
- **Database password rotation:** Free tier Render does not allow password changes in UI.
- **Admin interface aesthetics:** Still inconsistent with public face. Functional but bare.
- **RealDictCursor:** `get_db()` uses `RealDictCursor` globally — cache reads in `rocky_api` must use explicit `DictCursor` and key-based access (`row['title']` etc.) rather than tuple unpacking.

---

## Decisions Deferred / Future Work

### Lobe 3 — Rocky Reasoning
- Rocky thinking through a problem with the user
- Coming-soon page live at `/coming-soon/reasoning`

### Lobe 4 — Rocky Listening
- Rocky as confessor, sounding board, old friend
- Coming-soon page live at `/coming-soon/listening`
- Character details for this lobe: Rocky's favorite beer was Beamish (no longer available in the US). His favorite scotch was Oban. These specifics belong in Lobe 4's character definition.

### Time Machine — 10,000-year window refinement
- Currently roams freely across the Neolithic world — may benefit from regional anchoring if output feels disjointed in practice
- Revisit after more usage data

### Time Machine — "Ask Rocky more" feature
- After reading a daily narrative, user should be able to ask Rocky to go deeper
- Requires passing the generated narrative back into a new conversation context

### Lobe toggle UX
- Currently separate pages; eventually should feel like Rocky turning his attention rather than navigating between pages
- Transition design deferred until both active lobes are mature

### Database scaling
- Current: Render managed PostgreSQL, free tier
- Future: upgrade path needed for scale

---

## Aesthetic / Design Direction

- Dark background (#0A0A0A / #0E0E0E), gold accent (#C9A84C), contemplative and slightly mysterious
- Mobile-first layout, renders well on cell
- Rocky's Time Machine uses EB Garamond (serif) for narrative text — tactile weight
- Dream Engine uses Georgia throughout — warmer, more personal
- Color system: gold (dream), teal (time), blue (reason), purple (listen) — consistent across nav dots and era card pips

---

## Conceptual Notes

The Dream Engine and the Time Machine are not two different ideas. They are the same impulse pointing in opposite directions:
- The Dream Engine reaches **inward and forward** — into the collective subconscious, generating something new from pooled human truth.
- The Time Machine reaches **outward and backward** — into the collective memory, finding the human signal in the historical record.

Both refuse to let texture be lost. Both are Rocky.

Rocky's voice in the Time Machine: intimate, first-person, elegiac without being mournful. Speaking as if sitting with an old friend around a campfire late at night — not performing, not lecturing, just telling the truth about what he saw and what it meant.

The tagline: *"Every day is the echo of ten thousand days before it."*

---

## June 1, 2026

### Distill into Poetry feature — COMPLETE and deployed

- "Distill into poetry" button on result.html
- Calls /distill route, caches result client-side
- Claude API reshapes raw lines into structured poetic form
- 5 rotating recipes: structured, imagist, incantatory, fragmented, declarative
- Distilled poem renders in gold; "return to dream" toggle restores raw poem

---

## June 3, 2026

### Session summary — infrastructure and interface work

- Custom domain: dreamengine.lightclub.cloud (CNAME at Namecheap, SSL via Render)
- Mobile curation interface at /admin/mobile
- About page at /about with "what is this?" link in footer
- Poem line wrapping fixed with hanging indent
- 503 approved phrases as of this session

---

## June 5, 2026

### Rocky's Time Machine — COMPLETE and deployed

**What was built:**
- New Flask route `/time-machine` serving `templates/time_machine.html`
- New Flask route `/api/rocky` — receives system prompt, user prompt, and era_id; checks PostgreSQL cache; calls Anthropic API on cache miss; stores result; returns JSON
- Four temporal windows: 10 years (teal), 100 years (blue), 1,000 years (purple), 10,000 years (amber)
- Each window has: era label, year display, evocative title, Rocky's narrative (3-4 sentences), context pills (3 grounding facts), confidence bar
- Confidence bars fixed per era: 92% / 65% / 35% / 15%
- Daily caching in new `time_machine_cache` PostgreSQL table — one API call per era per day
- All four windows load simultaneously on page load
- "Show me something else" button removed — Rocky speaks once a day

**Rocky's voice:**
- System prompt: timeless witness, campfire intimacy, elegiac without mournful, never lectures, finds texture of daily life as significant as decisions of kings
- Prompts instruct Rocky to find a fresh entry point each time — never open with "Let me show you" or variants
- Broadly human — reaches beyond Western history intentionally

**Migration:**
- `migrate_time_machine_cache.py` — run once against live DATABASE_URL to create cache table
- Table: `id`, `cache_date`, `era`, `title`, `narrative`, `context_pills`, `created_at`
- UNIQUE constraint on `(cache_date, era)` — prevents duplicate daily entries

**Technical note — RealDictCursor gotcha:**
- `get_db()` sets `RealDictCursor` globally, which returns rows as dicts
- Tuple unpacking (`title, narrative, context_pills = row`) returns dict keys as values, not column data
- Fix: use `conn.cursor(cursor_factory=psycopg2.extras.DictCursor)` for cache reads and access by key: `row['title']`, `row['narrative']`, `row['context_pills']`

### Rocky's humours navigation — COMPLETE and deployed

- Persistent fixed nav bar at top of all pages
- Label: "Rocky's humours" (color #6a6560)
- Four colored dots: gold (Dream Engine), teal (Time Machine), blue (Reasoning), purple (Listening)
- Active dot: full opacity. Available: 0.3 opacity. Coming-soon: 0.15 opacity.
- Hover tooltip renders below dot (not above) — desktop only
- Body padding-top: 6rem on all pages to clear fixed bar

### Coming-soon pages — COMPLETE and deployed

- Route: `/coming-soon/<lobe>` — accepts 'reasoning' or 'listening'
- Template: `templates/coming_soon.html` — same dark aesthetic, same nav, Rocky's quote
- Rocky's quote (verbatim): *"I have to go to the hardware store to get more lumber. I'm all out. But don't worry, we'll get it done in time.... or we won't and you will be stuck wondering what it would have looked like."*
- These pages serve as architectural foundations for Lobes 3 and 4

### About page — updated

- Added Rocky's humours section: explains dot selector with inline illustration
- Added Rocky's Time Machine section: explains four windows, confidence bar, daily cadence
- Nav bar added for consistency

### result.html — updated

- Nav bar added for consistency with all other pages
- No other changes

*Paste this file (or relevant sections) at the start of a new session with Claude to restore project context quickly.*

---

## June 17, 2026

### Rocky's Renown — COMPLETE and deployed

**Concept:**
- Replaced Rocky Reasoning (Lobe 3) with Rocky's Renown — a public submission interface where anyone can add stories, opinions, facts, testimonials, or tall tales to Rocky's legend
- Philosophical grounding: Renown in the chivalric tradition is externally conferred — honor given, not internally generated. The lobe opens Rocky's Core outward, letting the legend grow the way legends actually do: through retelling, embellishment, and attribution
- Rocky as vessel for other people's fables — contributors who never knew Rocky can use him as a stand-in for their own loved ones, or simply add to the folk hero in the making
- Threshold inscription: *"Rocky was real. Rocky was also a legend. Add to both."*
- Design principle: Sacred ground. Low bar for entry.

**What was built:**

Public page `/renown`:
- Random Rocky Core seed entry displayed as prompt (unweighted — whimsy as welcome as grief)
- Submission form: entry type (Story / Opinion / Fact / Testimonial / Tall Tale), open text field, optional contributor attribution
- Success state on submission: "It's in the ledger. Every legend grows in the telling."
- Footer note: "Submissions are reviewed before they enter the record."

Admin queue — new tab "Rocky's Renown" in `/admin/phrases`:
- Loads pending submissions on tab click
- Each card shows: content, type badge, date, contributor (if provided)
- Significance selector (1–2–3) per submission before approval
- Approve writes directly to `rocky_core_entries` with `source='renown'`
- Reject discards without writing to Core
- Flash confirmation on approve/reject

**Schema changes:**
- `rocky_core_entries`: added `source VARCHAR(20) DEFAULT 'core' CHECK (source IN ('core', 'renown'))` and `contributor VARCHAR(100)` (nullable)
- New table `renown_submissions`: `id`, `entry_type`, `content`, `contributor`, `status` (pending/approved/rejected), `submitted_at`
- Migration: `migrate_renown.py` — run once against live DATABASE_URL

**Architectural decision:**
- Approved Renown entries feed directly into Rocky Core with `source='renown'` tag — they interact with all AI lobes (Time Machine, future Reasoning/Listening)
- Source tag preserved so the decision can be reversed or filtered by source if real-world experience warrants it

### Rocky's humours — recolored to Aristotelian elements

The four dots now carry explicit philosophical meaning:

| Lobe | Element | Color |
|---|---|---|
| Dream Engine | Water (Emotions) | Blue `#4A90D9` |
| Time Machine | Air (Intellect) | Yellow `#E8C547` |
| Rocky's Renown | Fire (Spirit) | Red `#C0392B` |
| Rocky Listening | Earth (Physical) | Green `#4CAF82` |

- All four templates updated: `index.html`, `time_machine.html`, `about.html`, `coming_soon.html`, new `renown.html`
- CSS class `.dot-reason` replaced with `.dot-renown` across all templates
- Accent colors on index and about updated from gold to blue to match Dream Engine's new water/emotion identity
- Time Machine internal era card colors (teal pip, confidence fills) left intact — those are the Time Machine's own visual language, independent of the humours scheme
- CSS variables in time_machine.html renamed: `--color-teal` → `--color-era-10`, `--color-gold` → `--color-accent`

### Coming-soon route — updated

- Removed `reasoning` lobe from coming-soon route
- Rocky Listening remains the only coming-soon destination
- `/renown` is now a live route, not a placeholder

*Paste this file (or relevant sections) at the start of a new session with Claude to restore project context quickly.*
