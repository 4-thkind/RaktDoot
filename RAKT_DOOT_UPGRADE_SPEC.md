# Rakt Doot: Upgrade Spec for Claude Code

> **Read this whole file before writing any code.** It describes what already exists in this repo, the weak spots to fix, the TinyFish upgrades, and a set of new AI features. It gives direction, not a fixed design. Where it suggests an approach, treat it as one reasonable option: if you find a cleaner or more robust way that fits the existing code, use it and say why in the PR/commit notes. The goal is a working, demoable product, not a literal implementation of this text.

---

## 0. Context

**Rakt Doot** (रक्त दूत) is a phone-first web app for finding blood in an emergency in India. A family member picks the patient's blood group and location. A **TinyFish** web agent reads live stock from **eRaktKosh** (the government blood-bank portal, which has no API). If nothing nearby has stock, the app alerts compatible, eligible, nearby donors on **WhatsApp**. Donors never install an app and are never spammed (rest periods enforced, at most one alert per day, quiet hours).

- **Team:** Pookie Blinders (Kartik Tiwari, Utkarsh Singh, Raaghav Kapoor)
- **Event:** Azinhack 2026, IoSC (Intel oneAPI Student Club), USAR GGSIPU. Open Innovation, **AI Engineering track**.
- **Hard requirement:** TinyFish must be *meaningfully* integrated and demoable.
- **What judges reward:** real AI (not wrapper calls), working code, a live demo, measurable claims, and visible TinyFish usage.

### 0.1 Stack as it exists

- **Backend:** Python FastAPI (`backend/app`), SQLAlchemy models, SQLite by default (`DATABASE_URL` can point at Postgres/Supabase), in-process ticker (`jobs/ticker.py`), pytest tests.
- **Frontend:** Next.js App Router + TypeScript (`frontend/app`), i18n (en/hi) in `lib/i18n.tsx`, SSE consumption, Supabase auth.
- **Messaging:** `services/whatsapp.py` supports `cloud | twilio | mock`. In mock mode the `/simulator` page *is* the WhatsApp channel.
- **TinyFish SDK:** `tinyfish` Python package (`AsyncTinyFish`, `agent.stream`, `search.query`). Docs: https://docs.tinyfish.ai, coding-agent summary: https://docs.tinyfish.ai/for-coding-agents.md, full reference: https://docs.tinyfish.ai/llms-full.txt. **Read the docs for exact field names before using a new API surface; don't guess.**
- **LLM:** any OpenAI-compatible endpoint via `LLM_API_KEY / LLM_BASE_URL / LLM_MODEL` (`services/llm.py`).

### 0.2 Already built (do NOT rebuild; extend instead)

| Area | Where | What it does |
|---|---|---|
| TinyFish Agent on eRaktKosh | `services/tinyfish_client.py` `lookup_stock` | Stealth browser, SSE progress, live `streaming_url` view, `validate_result`, per-(state, district, component) cache with TTL, stale-cache fallback, demo mode with labelled sample stock |
| TinyFish Search | `tinyfish_client.verify_hospital` (called in `api/requests.py`) | Token-overlap check that a hospital exists |
| Intent parser | `services/llm.py` | LLM JSON intent parse (en/hi/Hinglish) with keyword fallback, validated output, never decides eligibility |
| WhatsApp bot | `services/bot.py` | Onboarding, accept/decline, eligibility pre-screen, connect, on-way, follow-up, STOP/PAUSE, location update |
| Ranking | `core/ranking.py`, `scripts/train_ranker.py` | Weighted heuristic, Bayesian smoothing, features logged on each `Notification`; LR trainer + AUC on synthetic or DB logs |
| Dispatch | `services/dispatch.py` | SQL-enforced rest period, 24 h limit, quiet hours, waves over radii `5,10,25,40`, exploration pick, auto-close of pending donors |
| Ticker | `jobs/ticker.py` | Waves, expiry, on-way, follow-up, eligible-again |
| Eligibility | `core/eligibility.py`, `rules/eligibility.yaml` | Rule-based pre-screen |
| Compatibility | `core/compatibility.py` | Red-cell table, O− held in reserve |
| Frontend | `find/`, `request/[id]/`, `r/[slug]/`, `donate/`, `simulator/`, `admin/`, `ProximityPlate.tsx` | 5-step find flow, range map, live dashboard, share page, mock WhatsApp, admin reset/tick/stats |

### 0.3 Non-negotiable guardrails

1. **The emergency flow must never block** on a new feature. Every new external call has a timeout and a fallback, the same pattern `lookup_stock` already uses.
2. **Every new feature works without API keys** in a clearly labelled demo or sample mode, like the existing TinyFish demo mode, so the app runs end to end on a fresh clone.
3. **The LLM never makes medical decisions.** Eligibility stays deterministic. The LLM only parses, explains, or picks from a fixed set of safe actions.
4. **Never scrape personal data** (donor PII) from any site. TinyFish reads public, non-personal data only.
5. **No payment for blood**, anywhere. Flag messages that ask for money.
6. **Synthetic data stays labelled synthetic** (`synthetic=True`, the `9100000xxxxx` phone range, "sample" badges in the UI).
7. **Keep existing tests passing** (`backend/tests`). Add tests for each new piece of non-trivial logic.
8. **Follow existing conventions**: config in `config.py` via `_env`, strings in `services/messages.py` and `lib/i18n.tsx` (en and hi), SSE via `api/common.sse`, DB sessions via `session_scope` / `get_db`.
9. **Don't hardcode secrets.** Update `.env.example` (backend and frontend) for every new variable.
10. **Update `README.md`** at the end: new features, new env vars, the AI and TinyFish sections, and benchmark results.

---

## 1. Weak spots to fix first

These are real issues found in the current code. Fix them before or alongside the new features, since several features depend on them.

### W1. Blood component is a single global setting
- **Problem:** `settings.eraktkosh_component` (default "Packed Red Blood Cells") is used for every lookup. A dengue patient needing **platelets**, or a burns patient needing **plasma**, gets the wrong stock. Requests have no component field.
- **Fix direction:**
  - Add a `component` field to `Request` (default PRBC) and to the stock API (`/api/stock`, `/api/stock/stream`).
  - Pass it through to `lookup_stock` and include it in the cache key (the key already has a component slot).
  - Add a component picker to the find flow (default "Red cells", plus "Platelets", "Plasma", "Whole blood", "Don't know"). Map these to eRaktKosh's exact option labels; check the live dropdown.
  - **Compatibility differs per component.** Plasma is roughly the reverse of red cells (AB is the universal plasma donor). Platelet ABO matching is preferred but less strict. Add a per-component compatibility table in `core/compatibility.py`, keeping red cells as the current table, and mark the non-red-cell tables in comments and the README as "verify against NBTC/clinical guidance".
  - For donor dispatch, note in copy that platelet/plasma donation is usually apheresis at specific centres; the alert text should say which component is needed.

### W2. Blood-bank directory is seeded and matched by fuzzy name
- **Problem:** `attach_locations` matches eRaktKosh bank names to a seeded `blood_banks` table with 0.6 token overlap. Unmatched banks get no distance, and seeded coordinates are approximate.
- **Fix direction:** Build a real directory with TinyFish **Fetch** and/or the **Agent** from eRaktKosh's blood-bank listing pages (name, address, phone, category, licence, district). Geocode addresses once (the existing `geocode.py` uses Nominatim; respect its rate limits and cache results). Store `source="eraktkosh"` vs `"seed"`. Improve matching beyond token overlap: normalise names, compare address and phone too, and use a similarity score such as `rapidfuzz` if it's already a dependency, otherwise the stdlib `difflib`. Log unmatched banks so they can be fixed.

### W3. The agent returns prompt-formatted JSON instead of schema-validated output
- **Problem:** `GOAL_TEMPLATE` asks for JSON in prose, and `validate_result` cleans up afterwards.
- **Fix direction:** Use TinyFish's **structured output** (`output_schema` on the run; see https://docs.tinyfish.ai/key-concepts/structured-output.md) with a JSON Schema for the banks payload. Keep `validate_result` as a second line of defence, because "COMPLETED does not mean success".

### W4. No India proxy
- **Problem:** Government sites often throttle or block non-Indian IPs.
- **Fix direction:** Pass `proxy_config` with country `IN` (check the SDK enum name) on eRaktKosh runs, behind a config flag (`TINYFISH_PROXY_COUNTRY=IN`).

### W5. Hospital verification is shallow
- **Problem:** `verify_hospital` returns True if enough name tokens appear in top Search snippets. That's easy to fool and easy to miss.
- **Fix direction:** Return a **score plus evidence** (matched title, URL, address match, distance between the geocoded hospital and the claimed location) instead of a bool. Optionally Fetch the top result to confirm the address. Show "Verified hospital ✓ (source)" or "Couldn't verify" on the dashboard. Feed the score into Forward Checker (F2) and fraud signals.

### W6. TinyFish cost and latency aren't visible
- **Fix direction:** Record run ID, duration, step count and (if the API exposes it) credits per run. Show a small "Fetched by TinyFish agent · 34 s · run abc123" badge on the stock screen, and aggregate stats on `/admin`. This makes the integration visible to judges and helps tune the cache.

> Also scan the repo for anything else that looks broken or fragile while working (failing tests, unhandled exceptions in the SSE streams, timezone mistakes, missing i18n keys). Fix what you find and list it in the final notes.

---

## 2. TinyFish integration upgrade: Sense → Verify → Act → Learn

Current usage is one Agent goal on one site plus one Search call. That's thin for a sponsor requirement. Organise the integration into four layers, and make it visible in the UI and the README.

### 2.1 Sense
- **S1. Stock history at scale.** Batch lookups across all Delhi NCR districts (and any configured state list) using TinyFish's batch/async endpoints (`run-batch` / `agent.queue`, polled or via **webhooks**; see docs). Write every successful result into a new `stock_history` table (append-only snapshots). This feeds F1 (Shortage Radar).
- **S2. Monitor.** Use TinyFish **Monitor** (https://docs.tinyfish.ai/monitor/index.md) to watch eRaktKosh pages or topics on a schedule, if it fits better than the app's own ticker. Pick whichever is more reliable; document the choice.
- **S3. Multi-source adapter.** eRaktKosh is the primary source, but add an adapter layer so other public stock pages (state blood transfusion council sites, large hospital chain pages; find real candidates, don't invent URLs) can be read by the Agent into the **same schema**. Design it so a new source is just config (URL + goal + schema + parser). Even one extra working source makes the pitch "one API for every blood portal".

### 2.2 Verify
- **V1. Directory via Fetch** (see W2).
- **V2. Hospital verification with evidence** (see W5).
- **V3. Forward Checker verification** (F2): Search the phone number and hospital in a forwarded plea, and Fetch any URL inside it.

### 2.3 Act
- **A1. Camp finder.** eRaktKosh lists blood donation camps. Use the Agent or Fetch to pull upcoming camps (date, place, organiser, coordinates after geocoding) into a `camps` table. Use it in:
  - the "eligible again" message ("There's a camp near you on Saturday at …"),
  - the deferred-donor message ("Can't donate today? Here's the next camp after your deferral ends"),
  - F5 dispatcher actions and F10 camp placement.
- **A2. Optional assisted registration (stretch).** If eRaktKosh or a camp organiser has a **public** donor registration or camp sign-up form, let the Agent fill it in **on the donor's explicit consent** with data they provided. **Check first** that such a form exists and that automating it is acceptable. If it isn't, skip this and write down why. Never create accounts or submit anything without consent.

### 2.4 Learn: "Agent learns, Browser replays" (headline TinyFish feature)
- **Idea:** The Agent is flexible but slow (often 30–60 s) and costs credits. Once the Agent has successfully navigated eRaktKosh, the path it took (selectors or steps) can be saved and replayed deterministically on TinyFish's **Browser API** (remote browser over CDP; drive it with Playwright, which is preinstalled in many environments) in a few seconds for far fewer credits. If the replay fails (layout change, selector missing, empty or invalid result), fall back to the Agent, which re-learns and re-saves the path. **Self-healing scraping.**
- **One possible design** (choose your own if better):
  - Inspect the Agent run's steps (the runs API exposes steps; HTML snapshots are available with `capture_config.html`). If extracting selectors from the agent trace is impractical, write the replay script by hand for eRaktKosh's stock form, and use the Agent as the healing fallback plus a verifier that checks replay output against an occasional Agent run.
  - Store versioned "recipes" (`site`, `version`, `steps`, `created_from_run_id`, `success_count`, `fail_count`, `last_ok_at`).
  - `lookup_stock` tries in order: cache → replay recipe (Browser API) → Agent (and re-learn) → stale cache → unavailable.
  - Log which path served each request and the latency, and show it in the stock badge and `/admin` ("served by replay in 4.1 s" vs "agent in 41 s").
- **Tests:** replay success, replay failure falling back to the Agent, and recipe update after healing. Use recorded responses or fakes, the way `test_tinyfish_live.py` already fakes the stream.

### 2.5 Hygiene
- `output_schema` (W3), `proxy_config` IN (W4), cost/latency badges (W6).
- One `tinyfish_client` entry point per capability, all with timeouts, typed results, and demo-mode equivalents.
- A **TinyFish panel** on `/admin` listing recent runs (type, source, duration, status, run ID link) so the integration can be shown in the demo.

---

## 3. Feature specs

Each feature below has a goal, why it matters, where it likely plugs in, and acceptance criteria. Implement all of them. Choose internal designs freely within the guardrails.

### F1. Shortage Radar: predict shortages before the emergency
- **Goal:** Forecast, per (district, blood group, component), whether usable stock will drop below a threshold in the next 48–72 h, and act on it by sending a **pre-emptive donor drive** before an emergency happens.
- **Why:** It turns Rakt Doot from reactive to preventive, and it makes TinyFish the data engine. Delhi in October is dengue season, when platelet demand spikes.
- **Data:** `stock_history` from S1. Until enough real history exists, generate **clearly labelled synthetic history** (seasonality, weekday effects, festival and dengue spikes) so the model and UI can be demonstrated. Keep a flag separating real from synthetic rows.
- **Signals:** Optionally use TinyFish Search (`domain_type="news"`, `recency_minutes`) for news signals (dengue case reports, major accidents, festivals) as features, or TinyFish's **Research API** to produce a short cited "district blood situation" summary. Keep these optional and cached.
- **Model:** Your choice. A simple, explainable baseline (lag features + gradient boosting, or exponential smoothing per series) is fine. Include a backtest (e.g. MAE, or precision/recall on "will hit zero") and report it. Don't add heavy dependencies if a lighter one works.
- **Action:** When a shortage is predicted, propose (and on admin click, or automatically when configured) a **pre-emptive drive**: alert eligible, compatible donors near the at-risk bank to donate at that bank. Reuse the dispatch filters (rest period, 24 h limit, quiet hours) but in a separate "drive" request type, so these alerts don't look like emergencies. Respect the one-alert-per-day rule.
- **UI:** A "Shortage Radar" page: a map or grid of districts with risk per group and component, a time-to-shortage estimate, the model's top contributing factors, and a "Start donor drive" button. Mark synthetic data clearly.
- **Accept when:** history is collected from real lookups; a forecast endpoint returns risk per series; the backtest metrics are in the README; the radar page renders; a drive can be triggered and shows up in the simulator.

### F2. Forward Checker: kill zombie and scam blood forwards
- **Goal:** Anyone forwards a blood plea (copied from a WhatsApp group) to the Rakt Doot number. The bot extracts the details, checks whether the plea is fresh, real and not already handled, and replies with a verdict plus an action.
- **Where:** a new branch in `bot._free_text` (or before it) that detects plea-like messages (long text containing a blood group plus a phone number or hospital, or WhatsApp "forwarded" metadata if the webhook provides it). Also add a web version (paste box) on the site.
- **Pipeline:**
  - The LLM extracts structured fields (group, units, hospital, city, date, phone, patient name if present), validated like `llm._validate`.
  - Signals:
    - age of the date mentioned
    - how many times we've seen this phone or text (store hashes in a `forwards` table)
    - match against existing `Request`s (open or closed)
    - hospital verification score (W5)
    - TinyFish Search on the phone number and hospital (V3)
    - **scam patterns**: asks for money, UPI or "transport charges", or an unusual payment ask
  - The verdict is one of: `likely_stale`, `likely_fulfilled`, `unverified`, `looks_genuine`, `possible_scam`, each with short reasons.
  - Actions: for `looks_genuine`, offer "Alert N compatible donors near <hospital>?", which creates a request with the requester's consent, or tells them to ask the original poster to use the share link. For `possible_scam`, warn plainly and never forward it on.
- **Accept when:** works in the simulator and the web paste box in en and hi; has tests for extraction, staleness, duplicate detection and scam flagging; the verdict is explained in one or two lines.

### F3. Snap the requisition slip (vision intake)
- **Goal:** The requester photographs the hospital's blood requisition form, which is often handwritten, and the app pre-fills group, units, **component**, hospital, ward and urgency with nothing typed.
- **Where:** an optional "Scan slip" button at the start of `/find` → a new backend endpoint → a vision-capable LLM (OpenAI-compatible multimodal call; make the model configurable as `VISION_MODEL`) → structured JSON validated server-side → pre-fill the find flow. The user always confirms the fields.
- **Requirements:**
  - Return a confidence per field and highlight low-confidence fields for review.
  - Without a key, use a demo mode that returns a fixed sample parse for a bundled sample image, labelled as sample.
  - Downscale and compress images client-side. Don't store images longer than needed; delete them after parsing unless the user opts in.
  - This depends on W1 (component field).
- **Accept when:** a sample slip parses end to end into the flow; there are tests for validation and confidence handling.

### F4. Voice notes in any Indian language
- **Goal:** Requesters and donors can send WhatsApp **voice notes** in Hindi, Hinglish, English and ideally more Indian languages. Speech-to-text output feeds the existing pipeline: `parse_intent` for donors, and request extraction (shared with F2/F3) for requesters ("Papa ko B positive chahiye, Safdarjung mein, do unit").
- **Where:** `whatsapp_routes.py` inbound handlers (Cloud API sends audio as a media ID to download; Twilio sends a media URL). Add an STT service with pluggable providers: a hosted Indic STT (e.g. Sarvam), Whisper via API, or local Whisper (see F14 for an Intel OpenVINO option). The simulator should accept an uploaded audio file so this can be demoed in mock mode.
- **Optional:** text-to-speech for alerts, so donors who prefer audio get a short voice note alongside the text.
- **Accept when:** a voice note in the simulator creates a correct intent or request; it falls back gracefully without a key; the transcript is shown in the chat log.

### F5. Agentic dispatcher with visible reasoning
- **Goal:** Replace the fixed wave timer logic with an **LLM orchestrator** that chooses the next action from a **fixed, safe action set** based on live request state, and streams its reasoning to the dashboard as a "mission control" log.
- **Action set** (adjust as needed), each a thin wrapper over existing functions:
  - `wait(minutes)`
  - `send_next_wave(radius_km)` → `run_wave`
  - `widen_radius` → existing widen endpoint logic
  - `include_O_negative` (only when policy allows)
  - `recheck_stock(component, district)` → `lookup_stock`
  - `suggest_camp` (A1)
  - `suggest_public_share`
  - `close_if_fulfilled`
- **Guardrails:**
  - The SQL candidate filters (rest period, consent, 24 h limit, quiet hours) remain the **only** way donors are selected. The agent can't bypass them or message anyone directly.
  - Hard caps on total alerts per request and per time window.
  - If the LLM is unavailable or returns invalid output, fall back to today's deterministic wave logic.
  - Log every decision (state snapshot, chosen action, short reason) in a `dispatch_decisions` table.
- **UI:** stream decisions over the existing request SSE as a readable log, e.g. "2/4 connected · both 8+ km · 23:10 · B− scarce → widening to 15 km and allowing O−."
- **Optional:** expose TinyFish tools (Search, Fetch, Agent) to this orchestrator, for example to check another bank or find a camp, through the TinyFish SDK or the TinyFish MCP server.
- **Accept when:** a request runs end to end under the agent in the simulator with a visible log; there's a test that the fallback triggers on bad LLM output; caps are enforced.

### F7. Thalassemia autopilot (recurring needs)
- **Goal:** Thalassemia (and similar) patients need transfusions every 2–4 weeks for life. Let a family or blood centre register a **recurring need** (patient group, component, units, interval, hospital). The system schedules a fair rota of matched donors ahead of each due date, respecting rest periods and spreading load, and sends reminders and confirmations.
- **Where:** a new `recurring_needs` table; the ticker creates scheduled requests ahead of due dates; a scheduler module. OR-Tools CP-SAT or a simpler greedy-with-constraints approach both work. Prefer whatever is lighter and testable.
- **Constraints:** rest period per donor; max donations per donor per year; distance limit; prefer donors with high reliability; fairness (don't keep picking the same people); donor opt-in specifically for recurring patients.
- **UI:** register a need, see the upcoming schedule, and see which donor is confirmed for each date.
- **Accept when:** a 6-month schedule is generated for a seeded patient with no rest-period violations (test this); reminders appear in the simulator.

### F8. AI benchmark: make every AI claim measurable
- **Goal:** Judges trust numbers. Build an evaluation harness and put the results in the README and on a slide.
- **Sets:**
  - **Intent parsing:** 200+ labelled donor replies in English, Hindi (Devanagari) and Hinglish, covering accept, decline, ETA, location, eligibility yes/no, questions, STOP/PAUSE and noise. Compare the LLM against `rule_parse`: accuracy, per-intent F1, and the confusion matrix.
  - **Slip parsing (F3):** a small set of sample slips (synthetic or hand-made images), with field-level accuracy.
  - **Forward Checker (F2):** labelled pleas (stale, fulfilled, genuine, scam), with precision/recall per verdict.
  - **Forecast (F1):** backtest metrics.
  - **TinyFish:** success rate and latency for Agent vs replay (Section 2.4) over N runs.
- **Where:** `backend/eval/` with datasets as JSON/CSV and a single command (e.g. `python -m eval.run`) that prints a table and writes `docs/eval_results.md`. Must run offline in demo mode (rules-only numbers) and with keys (full numbers).
- **Accept when:** one command reproduces the numbers, and they're committed and linked from the README.

### F9. Proof-of-donation scan
- **Goal:** After donating, the donor photographs the donor card or receipt from the blood centre. A vision model reads the donation date and centre, so the rest period starts from a **verified** date instead of a self-reported "Yes, I donated".
- **Where:** the follow-up flow in `bot.followup` / ticker: after "Donated", ask for an optional photo. Reuse the F3 vision pipeline. Store `confirmed_by="photo"` on `Donation` (the field exists). Self-reported still works if no photo is sent.
- **Use:** verified donations count for badges and leaderboards, and the reliability score can weight them higher.
- **Accept when:** a sample card parses in the simulator and sets the donation date; there's a fallback without a key.

### F10. Camp placement AI
- **Goal:** Recommend **where** NGOs and colleges should hold their next blood donation camp, to fill the biggest gaps.
- **Inputs:** donor density (from `donors`), predicted shortages (F1), unmet or slow requests (request history), existing blood-bank and camp locations (W2, A1), and candidate venues (colleges and community centres, from a small seeded list or geocoded search).
- **Method:** your choice. A coverage/facility-location formulation (maximise unmet demand covered within X km, minus overlap with existing camps) or a weighted scoring over a grid both work. Explain the result ("covers ~N predicted-short donors within 5 km; nearest existing camp 9 km").
- **UI:** a map with top-k recommended sites and their reasons, and an export.
- **Accept when:** recommendations render for Delhi NCR with seeded data, with a unit test on the scoring.

### F11. Message bandit: learn which alert wording works
- **Goal:** Write 3–4 variants of the donor alert (urgency-forward, distance-forward, "why you"-forward, short). Learn online which variant gets the most acceptances, optionally per donor segment (language, age band, first-time vs repeat).
- **Method:** Thompson sampling (Beta-Bernoulli) per variant/segment, with reward = accepted (or connected). Store per-variant stats. Keep variant text in `messages.py` with en/hi versions, and **re-check WhatsApp template constraints**: templates need approval, so either register the variants as separate templates or only vary the parts that are free-form within the 24 h window. Document which.
- **UI:** an `/admin` chart of variant performance over time, plus the posterior means. Demoable with the simulator (simulated donor responses using a hidden true rate per variant, clearly labelled).
- **Accept when:** the bandit selects variants and updates from outcomes; there's a test that it converges on a simulated best variant.

### F12. "Why you" explanation in alerts
- **Goal:** Each alert includes a one-line reason generated from the ranker features: "You're 2.1 km away and B− is short in South Delhi today." Deterministic templating from `features` (plus F1 shortage data) is preferred over an LLM here: it's cheap, safe and fast.
- **Where:** `dispatch.alert_params` / `messages.py`. Make it a variant in F11 so its effect on response rate is measured.
- **Accept when:** alerts show a correct reason in en/hi; there are tests for the reason selection logic.

### F13. Family guide with cited answers (cited answers from official documents)
- **Goal:** A calm, cited Q&A for families and donors: what a replacement donor is, what cross-matching is, what to bring, how long it takes, what a blood bank can legally charge (processing charges per NBTC/government guidance; check the current source), whether one can donate after X, and so on.
- **Knowledge base:** official documents only (NBTC guidelines, MoHFW/NHM pages, eRaktKosh help pages, hospital pages), fetched with **TinyFish Fetch** and stored with source URLs. Chunk, embed (any embedding endpoint, or a lightweight local option), and retrieve. Answers **must** cite sources and must say "ask the blood centre doctor" for anything medical or personal. Refuse to answer outside the knowledge base.
- **Where:** a chat panel on the request dashboard and `/how-it-works`, plus the same answers on WhatsApp (replacing the current static `faq` reply when available).
- **Accept when:** answers include source links; out-of-scope questions are refused politely; there's a small eval (in F8) checking that answers cite a source and don't hallucinate on 20 test questions.

### F14. Intel oneAPI / OpenVINO angle
- **Goal:** The hosts are the Intel oneAPI Student Club. Run at least one model through Intel tooling and show it:
  - Whisper STT (F4) via **OpenVINO** (e.g. `optimum-intel` / OpenVINO GenAI), and/or
  - the F1 forecaster / F10 scoring with **Intel Extension for Scikit-learn** (`sklearnex`) or OpenVINO.
- **Requirements:** keep it optional (an extra requirements file or flag) so the main app installs without it. Add a short benchmark (latency CPU-default vs Intel-optimised) to F8's results.
- **Accept when:** a flag switches the optimised path on, and the benchmark numbers are in `docs/eval_results.md`.

---

## 4. Cross-cutting implementation notes

- **Shared extraction service.** F2, F3 and F4 all turn messy input (text, image, audio transcript) into a request-shaped object. Build one validated schema plus extractor and reuse it.
- **Shared vision service.** F3 and F9 share one module with demo fallbacks.
- **Config.** Add new settings to `config.py` with safe defaults. Suggested names: `VISION_MODEL`, `STT_PROVIDER`, `STT_API_KEY`, `EMBEDDING_MODEL`, `TINYFISH_PROXY_COUNTRY`, `TINYFISH_REPLAY_ENABLED`, `FORECAST_ENABLED`, `DISPATCH_AGENT_ENABLED`, `BANDIT_ENABLED`, `USE_OPENVINO`. Rename them if something cleaner fits.
- **DB changes.** The app currently creates tables from models. If you add a migration tool (e.g. Alembic), keep SQLite working. At minimum make sure a fresh DB and `admin/reset` still work. Update `seed.py` / `scripts/seed_donors.py` for new tables (camps, recurring needs, synthetic stock history, forwards).
- **Simulator and admin.** Every WhatsApp-side feature (F2, F4, F7, F9, F11) must be demoable from `/simulator` in mock mode: allow image and audio uploads there. Every background feature (F1, F10, S1, replay, bandit) gets a panel or button on `/admin`.
- **i18n.** All new user-facing strings in en and hi.
- **Performance.** Keep the requester's critical path fast. Heavy work (forecasting, batch scraping, embedding) runs in the ticker or background tasks, never inline in the emergency flow.
- **Privacy.** Phone numbers stay masked until acceptance. Images and audio are processed and dropped unless the user consents to storage. Hash forwarded texts in F2 rather than storing them raw where possible.
- **Tests.** Unit tests for each new core module; integration tests with recorded or faked external responses (TinyFish, LLM, STT, vision); keep `pytest` green.
- **Docs.** Update the README sections "Where the AI is", "TinyFish integration" (with the Sense/Verify/Act/Learn diagram), "API reference", "Setup" (new env vars), and "Future scope" (remove items that are now built). Add `docs/eval_results.md`.

---

## 5. Suggested dependency order (not a schedule)

Some pieces unblock others, so where possible:

1. W1 (component), W3 (`output_schema`), W4 (proxy), W6 (run telemetry)
2. W2 / V1 (real directory) and W5 / V2 (verification with evidence)
3. S1 (`stock_history`) → F1 (Shortage Radar)
4. Shared extraction + vision + STT services → F3, F2, F4, F9
5. F5 (agentic dispatcher), F12 → F11
6. A1 (camps) → F10, plus messages in the ticker
7. F7, F13, Section 2.4 replay, F14
8. F8 benchmark last (it measures everything), then the README

Re-order if the code suggests a better path.

---

## 6. Definition of done

- A fresh clone runs end to end with **no keys** (demo modes labelled) and with keys (live TinyFish, LLM, vision, STT).
- All existing and new tests pass.
- Every feature F1–F14 and every fix W1–W6 is either implemented or explicitly documented as not feasible, with the reason (e.g. the A2 form doesn't exist).
- The TinyFish integration covers Agent, Search, Fetch and Browser (and Monitor/batch if used), is visible in the UI, and is explained in the README.
- `docs/eval_results.md` contains real numbers produced by one command.
- A short `CHANGES.md` (or a README section) lists what was built, what changed in existing code, any bugs found and fixed, and any open risks.
