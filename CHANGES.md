# Changes: the Rakt Doot upgrade

What was built against `RAKT_DOOT_UPGRADE_SPEC.md`, what changed in existing code, bugs found and fixed, and open risks. Benchmark numbers are in [docs/eval_results.md](docs/eval_results.md) (one command: `cd backend && python -m eval.run`).

## Status by spec item

| Item | Status | Where |
|---|---|---|
| W1 component per request | Done. `Request.component`, `?component=` on `/api/stock` and `/api/stock/stream`, cache key, picker in `/find`, per-component compatibility (plasma and platelets marked "verify against NBTC"), alert text names the component and apheresis | `core/compatibility.py`, `api/stock.py`, `app/find` |
| W2 real directory | Done. 176 real Delhi NCR blood centres from eRaktKosh's public directory, geocoded once (Nominatim, cached, city-distance sanity check), `source="eraktkosh"`; matcher uses name + phone + address with `difflib`; unmatched banks listed on `/admin`; live refresh through TinyFish Fetch | `services/directory.py`, `services/eraktkosh.py`, `data/eraktkosh_directory.json` |
| W3 structured output | Done. `output_schema` (allowlisted keywords only) on Agent runs; `validate_result` kept as the second line of defence | `tinyfish_client.STOCK_SCHEMA` |
| W4 India proxy | Done. `TINYFISH_PROXY_COUNTRY=IN`. The SDK enum stops at 7 countries but the API accepts any ISO code (docs: `proxy_config.country_code`, e.g. `IN`), so the field is widened in a subclass | `tinyfish_client.proxy_config` |
| W5 hospital verification with evidence | Done. Score + evidence (directory match with distance to the claimed point, TinyFish Search hits with URL and address match); branch-aware for hospital chains; shown on the dashboard; feeds the Forward Checker | `tinyfish_client.verify_hospital` |
| W6 cost/latency visible | Done for duration, steps and run ID (the API exposes no per-run credit figure). Badge on the stock screen; TinyFish panel on `/admin` | `models.TinyFishRun`, `/api/admin/tinyfish` |
| S1 stock history + batch | Done. Every live/replay/batch result appends to `stock_history`; district sweeps use `POST /v1/automation/run-batch` and poll `runs.get` (and/or the run webhook); `STOCK_SWEEP_HOURS` or the `/admin` button | `tinyfish_client.batch_sweep`, `services/stock_history.py` |
| S2 Monitor | Done for news signals. Decision: the stock sweep stays on our ticker + run-batch, because Monitors are Fetch/Search only and cannot operate the stock form; a Topic monitor (dengue/platelet news) and a Page monitor (eRaktKosh notices) post to `/webhooks/tinyfish/monitor`, which stores `signals` for the radar | `/api/admin/tinyfish/monitors` |
| S3 multi-source | Partly. The replay/parse layer is data-driven (recipe steps + parser), and `services/eraktkosh.py` is the first adapter. Second-source candidates checked 2026-10-20: Assam SBTC's stock page (`assambloodbank.com/citizen/public/stock/availability`) was unreachable (Cloudflare 1001); bombaybloodgroup.org "Available Units" is reachable but lists rare Bombay-group units outside our 8-group schema. Not wired in; documented as next step | |
| V1, V2 | Done (W2, W5) | |
| V3 Forward Checker web signals | Done. Search on the phone number, Fetch on links inside the plea | `services/forwards.py` |
| A1 camps | Done. eRaktKosh camp schedule via TinyFish Fetch (organiser names and phones are dropped as personal data); labelled sample camps without a key; used in the eligible-again message, deferral messages, the dispatcher's `suggest_camp`, and camp placement | `services/camps.py` |
| A2 assisted registration | Done, demonstrated on a MOCK portal. The real camp sign-up needs a captcha, a mobile OTP and Aadhaar, so we built `/mock-portal` with exactly those steps (synthetic data only, clearly labelled). With consent, Rakt Doot reads the form, solves the captcha, submits the donor's details, and relays the OTP the donor receives; Aadhaar is used once, never stored, and masked in chat logs. Works on WhatsApp (one tap from any camp suggestion) and on `/camps`. `CAMP_PORTAL_URL` + a TinyFish key switches to a TinyFish Agent filling a public portal | `services/camp_registration.py`, `api/mock_portal.py` |
| 2.4 Agent learns, Browser replays | Done. Recipes are versioned data (`recipes` table); replay runs on the TinyFish Browser API through Playwright over CDP in a warm session; the Agent reports the option values it picked and a failed replay is healed by saving a new recipe version; every Nth replay is cross-checked by an Agent run. Order: cache → replay → Agent → stale cache → unavailable | `services/replay.py`, `tinyfish_client.lookup_stock` |
| F1 Shortage Radar | Done. Holt smoothing × weekday factor, risk = P(next 72 h below threshold), explainable factors, backtest, `/radar` page, donor drives as `kind="drive"` requests under the same SQL limits. History is synthetic and labelled until real history exists | `services/forecast.py`, `app/radar` |
| F2 Forward Checker | Done, in the WhatsApp bot (incl. voice notes) and at `/check`; hashes only, phone masked; verdict + 1-4 reasons in en/hi; consented request creation | `services/forwards.py` |
| F3 slip scan | Done. Client-side downscale, vision LLM (`VISION_MODEL`), per-field confidence, low-confidence highlighting, sample slip in demo mode, image dropped after parsing | `services/vision.py`, `components/ScanSlip.tsx` |
| F4 voice notes | Done, end to end. A family sends a voice note (or types) in Hindi, English or Hinglish; local Whisper transcribes it with no key (Sarvam / Whisper API optional); the shared extractor fills group, units, component and hospital (robust to garbled speech and Devanagari); the bot asks only for what is missing, shows nearby stock, confirms, alerts donors, and tells the family on WhatsApp when a donor is coming. Voice in → voice out: replies are also sent as voice notes (TTS: free Edge neural voices, Sarvam, or OpenAI-compatible), and donors can send VOICE ON. Mic on `/find` (browser speech recognition, server STT fallback) | `services/stt.py`, `services/tts.py`, `bot._request_flow` |
| F5 agentic dispatcher | Done. Fixed action set, policy check on O− release, hard caps, decision log streamed on the dashboard, deterministic fallback on missing key or bad output | `services/dispatch_agent.py` |
| F7 thalassemia rota | Done. Greedy scheduler with hard constraints and a fairness penalty, `/recurring` page, reminders with confirm/can't buttons, refill on decline, gap requests two days ahead | `services/recurring.py` |
| F8 benchmark | Done. `python -m eval.run` (offline) / `--live` | `backend/eval/` |
| F9 proof of donation | Done. After "Yes, I donated" the bot asks for the donor card; a readable, plausible date sets `confirmed_by="photo"` and the rest period; verified donations lead the leaderboard and the rota scoring | `bot._donor_card` |
| F10 camp placement | Done. Weighted coverage scoring with spread, reasons, map, CSV export | `services/camp_placement.py`, `app/camps` |
| F11 message bandit | Done. Thompson sampling per (variant, segment); five wordings registered as separate templates; admin chart; labelled simulation | `services/bandit.py` |
| F12 why-you line | Done. Deterministic from ranker features + radar shortage; it is the `why_you` bandit arm so its effect is measured | `core/explain.py` |
| F13 family guide | Done. Official pages only (eRaktKosh x2, DGHS/NBTC, a Delhi Govt hospital), BM25 retrieval, cited answers, refusal outside scope, "ask the blood centre doctor" for personal medical questions; on the dashboard, `/how-it-works` and WhatsApp | `services/guide.py` |
| F14 Intel oneAPI | Done for Intel Extension for Scikit-learn: camp-placement KMeans runs on `sklearnex` with `USE_INTEL_SKLEARN=true`; benchmark in the eval. OpenVINO Whisper: not done (multi-GB model download; STT providers above cover voice) | `services/camp_placement.py`, `eval/intel_bench.py` |

## Round 2 (after review)

- Product copy no longer frames Rakt Doot against the government portal; official stock records are described as one data feed Rakt Doot reads. Data credits remain where facts are cited.
- Voice-first requests, family updates, voice replies and assisted camp registration (above). 12 new tests (136 total).
- Fixed while building: SQLite lock wait (33 s) when a chat flow looked up stock from another thread; the bot now commits first. faster-whisper's PyAV loader breaks with current `av`, so audio is decoded by our own WAV reader or ffmpeg (added to the Docker image).

## Changes to existing behaviour

- **O− donors are held in reserve** for non-O− red-cell requests until the dispatcher allows them (wave 2+, a scarce group, or 20+ minutes short). Previously O− donors were only ranked lower.
- **The ticker's wave step is the agentic dispatcher** (`DISPATCH_AGENT_ENABLED=true`, rules without a key). With it off, the old `run_wave` timer runs unchanged.
- **Alert caps:** at most 60 alerts per request and 30 per hour (`MAX_ALERTS_PER_REQUEST*`).
- **Alert template changed:** `blood_request_alert` → `blood_request_alert_v2` (adds the component). Re-register templates from [docs/whatsapp-templates.md](docs/whatsapp-templates.md), now generated by `scripts/gen_templates.py`.
- **The static FAQ reply** is replaced by cited family-guide answers.
- **Seed data:** the 17 hand-made blood banks are replaced by the real eRaktKosh directory (an old DB that only has the hand-made list is upgraded on startup); 35% of synthetic donors opt in to rotas; one synthetic thalassemia patient; sample camps; the guide KB.
- **Schema upgrades without Alembic:** `init_db` adds missing columns with defaults (SQLite and Postgres), so existing databases and Docker volumes keep working. Tested on a copy of the old dev DB.
- Two existing test assertions now accept the Hindi message as well, because the O− reserve changes which donors a wave picks (the message is the same, in the donor's language).

## Bugs found and fixed

1. **Twilio webhook would crash:** `request.form()` needs `python-multipart`, which was not in `requirements.txt`. Added (also needed for uploads).
2. **Wrong-city geocodes:** Nominatim placed several Max hospital branches 250-420 km away (same name, other city). Directory geocoding now rejects results more than 40 km from the district's city.
3. **eRaktKosh responses are not always UTF-8** (cp1252 dashes) and crashed `json`; decoded with a fallback.
4. **Real eRaktKosh categories are `Charitable/Vol`**, so the "exclude charitable banks from hospitals" filter (`!= "Charitable"`) no longer excluded anything; and names like `Blood Centre, X Hospital (A Unit Of ...)` were shown raw. Fixed with `LIKE 'Charitable%'` and a name cleaner.
5. **Hospital chains matched the wrong branch** in verification; it now prefers the branch near the claimed location.
6. **Guide answered off-topic questions containing "stock"** ("stock price of Infosys"); the domain check now requires blood/donation terms.
7. **First-person requests on WhatsApp** ("Papa ko B positive chahiye...", typed or as a voice note) were marked "unverified: no number to call"; the sender's own number is now the contact, so they get the genuine verdict and the alert-donors offer. Hinglish postpositions ("Safdarjung hospital *mein*") are stripped from hospital names.
8. **Radar calibration:** a fixed threshold made rare groups (AB−, which usually hold 1-2 units) show ~100% risk everywhere; the threshold is now capped at a third of each series' usual level, so rare groups flag only when about to hit zero.
9. Frontend type check failed on a fresh machine because `@supabase/supabase-js` was in `package.json` but not installed (`npm install` fixes; no code change).

## Open risks

- **Live TinyFish paths are tested with recorded/faked responses only.** No `TINYFISH_API_KEY` was available while building, so Agent-vs-replay latency in the benchmark is "not measured"; run `python -m eval.run --live --tinyfish 5` with a key. The replay step template mirrors the XHR calls eRaktKosh's own page makes (checked live on 2026-10-20); if the site adds a captcha or token to those calls, replay will fail and the Agent serves (by design), but the recipe stays retired until the Agent heals it.
- **Plasma and platelet compatibility tables are simplified** and must be checked against NBTC/clinical guidance before real use.
- **Forecasts run on labelled synthetic history** until 14+ days of real `stock_history` exist per series; the backtest proves the pipeline, not real accuracy.
- **WhatsApp templates must be (re)approved** by Meta before live use; until the five alert variants are approved, run with `BANDIT_ENABLED=false`.
- **TinyFish webhooks are unsigned** (no signing in the docs); the receiver requires a secret `?key=` and never trusts the payload (it re-fetches the run by ID with our key).
- **Background ticker vs. admin reset:** a tick running while `/api/admin/reset` wipes tables can log `StaleDataError` once; the tick is retried on the next cycle.
- **SQLAlchemy's compiled extensions are blocked by Windows Application Control on the dev laptop.** Local runs used a venv with SQLAlchemy's pure-Python modules; Docker is unaffected.
