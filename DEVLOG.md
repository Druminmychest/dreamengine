# DEVLOG — Rocky's Dream Engine
*Maintained by: Rob Roach (robertdroach)*
*Last updated: June 1, 2026*

---

## Project Summary

An art project / web application combining the I Ching oracle structure with surrealist exquisite corpse poetry generation. Users submit phrases anonymously, a human curator assigns them to one of 64 I Ching hexagrams, and the system generates a poem drawn from the dream pool when a user submits a new phrase.

The project is a deliberate collaboration between human unconscious (phrase contributions) and AI assembly — the AI is a co-creator, not a tool.

---

## Core Concept

- 64 I Ching hexagrams act as organizational buckets for submitted phrases
- User submits a phrase → system runs an I Ching consultation algorithmically → identifies a hexagram → draws N phrases randomly from that hexagram's pool → assembles exquisite corpse poem → returns poem to user alongside traditional hexagram text
- A human curator (Rob) reviews all submitted phrases before they enter the dream pool, assigning each to a hexagram intuitively
- The curation step is intentional — the curator's unconscious shapes the pool

---

## Current Status (as of June 1, 2026)

**LIVE and deployed at: https://dreamengine.onrender.com**

### What is working:
- Public submission interface (mobile-first, visually rich, dark palette with gold accents)
- I Ching consultation algorithm
- Exquisite corpse poem generator drawing from PostgreSQL dream pool
- Poem + hexagram text returned to user as oracle reading
- Protected admin curation interface at `/admin/phrases` (HTTP Basic Auth)
- Admin can approve/reject phrases and assign hexagram from dropdown
- PostgreSQL database on Render (Ohio region)
- GitHub repo: https://github.com/Druminmychest/dreamengine

### Database state:
- Approximately 156+ approved phrases in the dream pool at last check
- Seed dataset drawn from Rob's own artistic writings
- PostgreSQL (upgraded from SQLite during deployment phase)

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

### Key files:
- `app.py` — main Flask application, all routes
- `templates/index.html` — public submission interface
- `templates/result.html` — oracle/poem output page
- `requirements.txt` — Flask, gunicorn, requests, beautifulsoup4, psycopg2
- `Procfile` — `web: gunicorn app:app`

### Environment variables (set in Render dashboard, NOT in code):
- `DATABASE_URL` — PostgreSQL connection string
- `ADMIN_USERNAME` — admin login
- `ADMIN_PASSWORD` — admin password

---

## Architecture Decisions (and why)

**SQLite → PostgreSQL:** Migrated during deployment. SQLite fine for local dev; PostgreSQL needed for hosted environment and future scale.

**Single file app.py:** Intentional for PoC simplicity. Will need reorganization before scaling.

**Anonymous contributions:** No accounts, no identifying information. Contributor token only.

**Human curation layer:** All phrases pass through Rob's intuitive hexagram assignment before entering the pool. This is a feature, not a bottleneck — it's where the artistic intelligence lives.

**Mobile-first web (not native app):** Lower barrier, no app store, easier to iterate. Native app is a future consideration.

---

## Known Limitations / Technical Debt

- **Render free tier spin-down:** First load after 15 minutes of inactivity takes 30–60 seconds. Beta testers should be warned.
- **Database password rotation:** Free tier Render does not allow password changes in the UI. Credential has appeared in chat history — be mindful of further exposure.
- **Admin interface:** Still relatively bare HTML compared to public face. Functional but inconsistent aesthetically. Not urgent pre-beta.
- **Return button on result page:** May be too subtle on mobile — worth user testing.

---

## Decisions Deferred / Future Work

### Poetic Form Filter ("Impose Poetic Form" toggle)
- Discussed imposing Adj-Noun-Verb-Adj-Noun structure on output assembly
- Decision: deferred. Surrealist argument against uniform structure is valid; raw output may be more generatively powerful.
- If revisited: toggle on output side (not submission), submissions stay raw in DB, NLP library (spaCy) at assembly time. Graceful fallback needed for surrealist phrases that resist parsing.
- **NLP = Natural Language Processing** — library-based part-of-speech tagging (spaCy is the recommended Python library)

### Rocky the Character
- A character/persona associated with the project
- Design intentionally deferred — will become clearer as the project develops
- Not in the current interface

### Database scaling
- Current: Render managed PostgreSQL, free tier
- Future: Will need upgrade path for millions of entries and concurrent users
- Flask + SQLAlchemy makes PostgreSQL migration straightforward when needed

### Native mobile app
- Future consideration after web interface is proven
- Current responsive web-first approach is the right scale for now

### Beta testing
- Planned: small subset of human beta testers pre-launch during PoC phase
- Will also contribute to seed phrase pool during beta

---

## Aesthetic / Design Direction

- Dark background, gold accent (#C9A84C), contemplative and slightly mysterious
- Mobile-first layout
- Minimal friction on submission — single input, low barrier
- Poem has breathing room on result page
- Whimsical and visually rich rather than clinical

---

## Conceptual Notes (for context in future sessions)

The project intentionally frames AI as collaborator rather than tool — the same way Rob's unconscious is imprinted on the seed pool, the AI's aggregate-of-human-expression nature is acknowledged as a structural element. The two "fishbowls" working together is a core metaphor.

The gamification loop: you contribute something of yourself anonymously → you receive something unexpected back. That exchange sustains participation.

---
## June 1, 2026

### Distill into Poetry feature — COMPLETE and deployed

**What was built:**
- "Distill into poetry" button on result.html — gold, visually distinct
- Calls /distill route in app.py on first click, caches result for subsequent toggles
- Claude API (claude-opus-4-5) reshapes raw exquisite corpse lines into Adj Noun, Verb — Adj Noun pattern
- If a line resists parsing, Claude draws a replacement from the emotional territory of surrounding lines
- Distilled poem renders in gold (#C9A84C) with "distilled form" label
- "Return to dream" toggle restores raw poem
- Raw submissions remain untouched in database — distillation is output-only

**Technical notes:**
- anthropic library added to requirements.txt
- ANTHROPIC_API_KEY set as environment variable in Render
- Distilled result cached client-side — API called once per session per poem

**Philosophical note:**
Distillation is framed as interpretation, not transformation. The dream cannot be changed, only read differently. Claude's reshaping is the programmatic equivalent of the human curation layer — a collaborator, not an editor.

---
## June 3, 2026

### Session summary — significant infrastructure and interface work

**Custom domain:**
- DNS CNAME record added at Namecheap: dreamengine.lightclub.cloud → dreamengine.onrender.com
- SSL certificate provisioned by Render automatically
- Project now live at: https://dreamengine.lightclub.cloud

**Mobile curation interface — COMPLETE:**
- New route /admin/mobile with mobile-optimized layout
- One phrase at a time, large touch targets, comfortable thumb navigation
- Approve/reject redirects immediately to next phrase
- Remaining phrase count displayed
- Same HTTP Basic Auth protection as desktop admin

**Distill function — recipe variety added:**
- Single Adj-Noun-Verb-Adj-Noun pattern replaced with 5 rotating recipes chosen randomly per call
- Recipes: structured, imagist, incantatory, fragmented, declarative
- Model updated from claude-opus-4-5 to claude-haiku-4-5-20251001 (faster, cost-efficient)
- Recipe name returned in JSON but not displayed to user — preserves mystery
- $5 Anthropic API credit added for testing; monitor at console.anthropic.com

**About page — COMPLETE:**
- New route /about with full project description
- "what is this?" link added to index.html footer, gold colored, centered on own line
- Text anchored around: "a surrealist oracle built from collective human expression"
- Oblique strategies framing added for creative use of output
- "ghosts of other human's emotions — impressions of their lives on the coalbed of human expression" — Rob's phrase, used verbatim

**Interface refinements:**
- Poem line wrapping fixed with hanging indent (text-indent: -1rem, padding-left: 2rem)
- Footer contrast improved across index.html
- "what is this?" link separated onto own centered line to prevent mobile wrap

**Dream pool status:**
- 503 approved phrases as of this session
- 149 additional phrases imported from new seed batch
- import_seed.py updated to write directly to PostgreSQL via DATABASE_URL environment variable
- migrate_to_postgres.py and seed_hexagrams.py added to .gitignore

**Known issues / deferred:**
- Render free tier spin-down still in effect — upgrade to $7/month Starter when ready for beta
- Database password rotation not possible on Render free tier UI
- Admin interface aesthetics still inconsistent with public face

**Exquisite corpse mode — considered and deferred:**
- Discussed adding a toggle for classical exquisite corpse interaction mode
- Decision: deferred. Pulls in a different direction from the core oracle identity.
- Worth revisiting as a separate project rather than a feature of this one.

*Paste this file (or relevant sections) at the start of a new session with Claude to restore project context quickly.*
