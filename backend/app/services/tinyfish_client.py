"""TinyFish integration: Sense -> Verify -> Act -> Learn.

eRaktKosh shows live blood stock per blood centre but has no public API. Lookups go:

    cache -> replay recipe (Browser API, ~seconds) -> Agent (and re-learn) -> stale cache -> unavailable

- Agent: a TinyFish web agent operates the Stock Availability form (state, district, group,
  component), returns schema-validated JSON (output_schema, W3) through an Indian proxy (W4),
  and reports the option values it picked so the recipe can learn them.
- Replay: services/replay.py runs the learned recipe on the TinyFish Browser API with Playwright.
- Search: hospital verification with evidence (W5), forward checking (F2), news signals (F1).
- Fetch: the blood-bank directory (W2), camps (A1), the family-guide sources (F13).
- Batch + Monitor: district sweeps into stock_history (S1) and scheduled news watching (S2).

Every call is recorded in tinyfish_runs (W6) and shown on /admin. Results are cached per
(state, district, component) so cost scales with districts, not users.

Modes: live (TINYFISH_API_KEY set) or demo (sample stock generated from our blood-bank table,
clearly labelled as sample data in the API and the UI)."""
import asyncio
import hashlib
import importlib.util
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select

from ..config import settings
from ..core.compatibility import ERAKTKOSH_COMPONENT, GROUPS, normalize_component, normalize_group
from ..core.geo import haversine_km
from ..db import session_scope, utcnow
from ..models import BloodBank, Recipe, StockCache, TinyFishRun

log = logging.getLogger("raktdoot.tinyfish")
Emit = Callable[[dict], Awaitable[None]]
AGENT_API = "https://agent.tinyfish.ai"

GOAL_TEMPLATE = """You are on the eRaktKosh "Stock Availability" page of the Government of India.
1. In "Select State" choose "{state}".
2. Wait for the district list to load. In "Select District" choose the option that best matches "{district}". If nothing is close, choose "All".
3. In "Select Blood Group" choose "All Blood Groups".
4. In "Select Blood Component" choose "{component}".
5. Click Search and wait for the results table. Read the "Government Blood Banks" tab and the "Other Blood Banks" tab.

Return the result in the output schema:
- district_selected: the district option you chose.
- form_values: the HTML value attribute of the selected option in each of the State, District and Blood Component dropdowns.
- banks: at most 25 banks, in the order shown. The Blood Bank cell often contains the name, address and phone together; split them into the fields.
- stock: the number of units shown for each group. Use 0 for a group shown as not available. Leave out groups that are not mentioned. Ignore Bombay groups (Oh+Ve, Oh-Ve).
- availability_text: the Availability cell text exactly as shown.
- If the table is empty, return an empty banks list.
- If a captcha, an error page or an access block appears, set error to a short reason."""

_GROUP_PROPS = {g: {"type": "integer", "minimum": 0} for g in GROUPS}
# Structured output (W3). Only keywords from TinyFish's allowlist; validate_result stays as a second line of defence.
STOCK_SCHEMA = {
    "type": "object",
    "properties": {
        "district_selected": {"type": "string", "nullable": True},
        "error": {"type": "string", "nullable": True},
        "form_values": {"type": "object", "nullable": True, "properties": {
            "state_value": {"type": "string", "nullable": True},
            "district_value": {"type": "string", "nullable": True},
            "component_value": {"type": "string", "nullable": True}}},
        "banks": {"type": "array", "maxItems": 25, "items": {"type": "object", "properties": {
            "name": {"type": "string"}, "address": {"type": "string", "nullable": True},
            "phone": {"type": "string", "nullable": True}, "category": {"type": "string", "nullable": True},
            "type": {"type": "string", "nullable": True}, "last_updated": {"type": "string", "nullable": True},
            "availability_text": {"type": "string", "nullable": True},
            "stock": {"type": "object", "properties": _GROUP_PROPS}},
            "required": ["name"]}},
    },
    "required": ["banks"],
}

_locks: dict[tuple, asyncio.Lock] = {}


# ---------------------------------------------------------------- plumbing
def _proxy_on() -> bool:
    return settings.tinyfish_proxy_country.lower() not in ("", "off", "none")


def proxy_config():
    """ProxyConfig with any ISO country. The SDK enum stops at 7 countries, but the API takes any
    alpha-2 code (docs: proxy_config.country_code, e.g. "IN"), so the field is widened here."""
    if not _proxy_on():
        return None
    from tinyfish import ProxyConfig

    class _AnyCountryProxy(ProxyConfig):
        country_code: str | None = None

    return _AnyCountryProxy(enabled=True, country_code=settings.tinyfish_proxy_country.upper())


def _client(timeout: float | None = None):
    from tinyfish import AsyncTinyFish

    return AsyncTinyFish(api_key=settings.tinyfish_api_key, **({"timeout": timeout} if timeout else {}))


def record_run(kind: str, purpose: str, status: str, started: float, target: str = "", run_id: str | None = None,
               steps: int | None = None, error: str | None = None, source: str = "eraktkosh") -> None:
    """Telemetry (W6). Never raises."""
    try:
        with session_scope() as db:
            db.add(TinyFishRun(kind=kind, purpose=purpose, status=status, target=target[:160], run_id=run_id, steps=steps,
                               error=(error or None) and error[:300], source=source,
                               duration_ms=int((time.monotonic() - started) * 1000)))
    except Exception as e:  # noqa: BLE001
        log.info("could not record tinyfish run: %s", e)


def _clean_banks(raw_banks: list) -> list[dict]:
    banks = []
    for b in raw_banks[:25]:
        if not isinstance(b, dict) or not str(b.get("name") or "").strip():
            continue
        stock = {}
        for k, v in (b.get("stock") or {}).items():
            g = normalize_group(str(k))
            try:
                n = int(v)
            except (TypeError, ValueError):
                continue
            if g and n >= 0:
                stock[g] = n
        banks.append({
            "name": str(b["name"]).strip()[:200],
            "address": (str(b.get("address")).strip()[:300] or None) if b.get("address") else None,
            "phone": (str(b.get("phone")).strip()[:40] or None) if b.get("phone") else None,
            "category": b.get("category"),
            "type": b.get("type"),
            "last_updated": b.get("last_updated"),
            "availability_text": str(b.get("availability_text") or "")[:300],
            "stock": stock,
        })
    return banks


def validate_result(result) -> tuple[list[dict] | None, str | None]:
    """COMPLETED does not mean the goal succeeded. Return (banks, error)."""
    if isinstance(result, str):
        return None, "agent returned text, not JSON"
    if isinstance(result, list):  # tolerate a bare list of banks
        return _clean_banks(result), None
    if not isinstance(result, dict):
        return None, "empty result"
    if result.get("error"):
        return None, str(result["error"])[:200]
    banks = result.get("banks")
    if not isinstance(banks, list):
        return None, "bad_shape"
    text = str(result).lower()
    if not banks and any(w in text for w in ("captcha", "blocked", "access denied")):
        return None, "blocked"
    return _clean_banks(banks), None


def attach_locations(banks: list[dict], directory: list, origin: tuple[float, float] | None) -> list[dict]:
    """eRaktKosh's table has no coordinates; match each bank to our directory (name, phone and
    address similarity, see services/directory.py) to get a location and distance."""
    from .directory import best_match

    for b in banks:
        if b.get("lat") is None:
            best, score = best_match(b, directory)
            if best is not None:
                b["lat"], b["lng"] = best.lat, best.lng
                b["phone"] = b.get("phone") or best.phone
                b["address"] = b.get("address") or best.address
                b["match_score"] = round(score, 2)
        if origin and b.get("lat") is not None:
            b["distance_km"] = round(haversine_km(origin[0], origin[1], b["lat"], b["lng"]), 1)
        else:
            b.setdefault("distance_km", None)
    banks.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 0))
    return banks


def _demo_banks(state: str, district: str, origin: tuple[float, float] | None, component: str = "prbc") -> list[dict]:
    """Deterministic sample stock (changes hourly) so the full flow can be shown without a key."""
    with session_scope() as db:
        rows = db.scalars(select(BloodBank)).all()
    if origin:
        rows = sorted(rows, key=lambda r: haversine_km(origin[0], origin[1], r.lat, r.lng))[:12]
    else:
        rows = [r for r in rows if r.district.lower() == district.lower()][:12]
    hour = utcnow().strftime("%Y%m%d%H")
    scarce_component = component in ("platelets",)  # platelets keep 5 days, so stock is thin
    banks = []
    for r in rows:
        stock = {}
        for g in GROUPS:
            h = int(hashlib.sha256(f"{r.name}{g}{component}{hour}".encode()).hexdigest(), 16)
            scarce = g.endswith("-") or scarce_component
            stock[g] = 0 if h % (2 if scarce else 4) == 0 else h % (4 if scarce else 18)
        banks.append({"name": r.name, "address": r.address, "phone": r.phone, "category": r.category,
                      "type": "Blood Centre", "last_updated": datetime.now(ZoneInfo(settings.timezone)).strftime("%d-%m-%Y %H:00"),
                      "availability_text": "", "stock": stock, "lat": r.lat, "lng": r.lng})
    return banks


# ---------------------------------------------------------------- recipes (Learn)
def active_recipe() -> Recipe | None:
    from . import replay
    with session_scope() as db:
        r = db.scalar(select(Recipe).where(Recipe.site == replay.SITE, Recipe.active.is_(True)).order_by(Recipe.version.desc()))
        if r:
            db.expunge(r)
        return r


def ensure_recipe() -> Recipe:
    """Version 1 is the step template with no learned codes; the Agent fills them in over time."""
    from . import replay
    r = active_recipe()
    if r:
        return r
    with session_scope() as db:
        r = Recipe(site=replay.SITE, version=1, steps=replay.DEFAULT_STEPS, learned={}, created_from_run_id=None)
        db.add(r)
        db.flush()
        db.expunge(r)
        return r


def _recipe_result(recipe_id: int, ok: bool) -> None:
    from . import replay
    with session_scope() as db:
        r = db.get(Recipe, recipe_id)
        if not r:
            return
        if ok:
            r.success_count += 1
            r.last_ok_at = utcnow()
        else:
            r.fail_count += 1
            # retire after repeated failures since the last success; the Agent then serves and re-learns
            recent_ok = r.last_ok_at and utcnow() - r.last_ok_at < timedelta(hours=6)
            if r.fail_count >= replay.FAILS_BEFORE_RETIRE and not recent_ok:
                r.active = False


def learn_from_agent(state: str, district: str, component: str, form_values: dict | None, run_id: str | None, healed: bool) -> int | None:
    """Merge the option values the Agent reported into the recipe. After a replay failure (healed=True)
    this saves a new recipe version, so the next lookup replays again."""
    from . import replay
    fv = form_values if isinstance(form_values, dict) else {}
    learned_bits = {}
    if re.fullmatch(r"-?\d{1,6}", str(fv.get("state_value") or "")):
        learned_bits.setdefault("states", {})[state] = str(fv["state_value"])
    if re.fullmatch(r"-?\d{1,6}", str(fv.get("district_value") or "")):
        learned_bits.setdefault("districts", {})[f"{state}/{district}"] = str(fv["district_value"])
    if re.fullmatch(r"\d{1,6}", str(fv.get("component_value") or "")):
        learned_bits.setdefault("components", {})[component] = str(fv["component_value"])
    with session_scope() as db:
        cur = db.scalar(select(Recipe).where(Recipe.site == replay.SITE).order_by(Recipe.version.desc()))
        learned = {k: dict(v) for k, v in ((cur.learned if cur else {}) or {}).items()}
        for k, v in learned_bits.items():
            learned.setdefault(k, {}).update(v)
        if cur is None or healed or not cur.active:
            for old in db.scalars(select(Recipe).where(Recipe.site == replay.SITE, Recipe.active.is_(True))):
                old.active = False
            new = Recipe(site=replay.SITE, version=(cur.version + 1) if cur else 1, steps=replay.DEFAULT_STEPS,
                         learned=learned, created_from_run_id=run_id)
            db.add(new)
            db.flush()
            return new.version
        cur.learned = learned
        return cur.version


async def _try_replay(state: str, district: str, component: str) -> tuple[list[dict], dict] | None:
    from . import replay
    if not settings.tinyfish_replay_enabled:
        return None
    recipe = ensure_recipe()
    started = time.monotonic()
    target = f"{state}/{district}/{component}"
    try:
        async with asyncio.timeout(45):
            banks, meta = await replay.run(recipe.steps, recipe.learned, state, district, component)
        if not banks:
            raise replay.ReplayError("empty result")
    except Exception as e:  # noqa: BLE001  (ImportError if Playwright is missing, ReplayError, timeouts...)
        reason = "timeout" if isinstance(e, TimeoutError) else str(e)[:200]
        log.info("replay %s failed: %s", target, reason)
        _recipe_result(recipe.id, False)
        record_run("replay", "stock", "failed", started, target, run_id=f"recipe-v{recipe.version}", error=reason)
        return None
    _recipe_result(recipe.id, True)
    record_run("replay", "stock", "ok", started, target, run_id=f"recipe-v{recipe.version}")
    return banks, {**meta, "recipe_version": recipe.version, "recipe_id": recipe.id}


# ---------------------------------------------------------------- Agent
async def run_stock_agent(state: str, district: str, component: str, emit: Emit) -> dict:
    """One Agent run. Returns {"banks", "run_id", "streaming_url", "steps", "form_values"}; raises on failure."""
    from tinyfish import BrowserProfile, CompleteEvent, ProgressEvent, StartedEvent, StreamingUrlEvent

    label = ERAKTKOSH_COMPONENT[component][0]
    goal = GOAL_TEMPLATE.format(state=state, district=district, component=label)
    run_id = streaming_url = None
    steps = 0
    result = None
    started = time.monotonic()
    try:
        async with asyncio.timeout(settings.stock_timeout_s):
            kw = {"url": settings.eraktkosh_stock_url, "goal": goal, "browser_profile": BrowserProfile.STEALTH, "output_schema": STOCK_SCHEMA}
            if proxy_config() is not None:
                kw["proxy_config"] = proxy_config()
            async with _client().agent.stream(**kw) as stream:
                async for event in stream:
                    if isinstance(event, StartedEvent):
                        run_id = event.run_id
                        await emit({"type": "progress", "message": "Agent opened eRaktKosh.", "run_id": run_id})
                    elif isinstance(event, StreamingUrlEvent):
                        streaming_url = event.streaming_url
                        await emit({"type": "agent_view", "streaming_url": streaming_url})
                    elif isinstance(event, ProgressEvent):
                        steps += 1
                        await emit({"type": "progress", "message": event.purpose})
                    elif isinstance(event, CompleteEvent):
                        run_id = event.run_id or run_id
                        if str(event.status).upper().endswith("COMPLETED"):
                            result = event.result_json
                        else:
                            raise RuntimeError(f"run {event.status}: {event.error.message if event.error else ''}")
                        break
        banks, error = validate_result(result)
        if error:
            raise RuntimeError(error)
    except Exception as e:
        reason = "timeout" if isinstance(e, TimeoutError) else str(e)[:200]
        record_run("agent", "stock", "failed", started, f"{state}/{district}/{component}", run_id, steps, reason)
        e.run_id, e.streaming_url = run_id, streaming_url  # type: ignore[attr-defined]
        raise
    record_run("agent", "stock", "ok", started, f"{state}/{district}/{component}", run_id, steps)
    return {"banks": banks, "run_id": run_id, "streaming_url": streaming_url, "steps": steps,
            "form_values": (result or {}).get("form_values") if isinstance(result, dict) else None}


async def verify_replay(state: str, district: str, component: str, replay_banks: list[dict], recipe_id: int) -> bool:
    """Occasional Agent run that cross-checks a replay (same banks and the same stock for most of them)."""
    async def quiet(_):
        return None
    try:
        agent = await run_stock_agent(state, district, component, quiet)
    except Exception:  # noqa: BLE001
        return False
    a = {re.sub(r"\W+", "", b["name"].lower()): b["stock"] for b in agent["banks"]}
    r = {re.sub(r"\W+", "", b["name"].lower()): b["stock"] for b in replay_banks}
    common = set(a) & set(r)
    ok = bool(common) and sum(a[k] == r[k] for k in common) >= 0.7 * len(common)
    with session_scope() as db:
        rec = db.get(Recipe, recipe_id)
        if rec:
            if ok:
                rec.verify_ok += 1
            else:
                rec.verify_mismatch += 1
    if not ok:
        learn_from_agent(state, district, component, agent.get("form_values"), agent.get("run_id"), healed=True)
    return ok


# ---------------------------------------------------------------- the lookup
async def lookup_stock(state: str, district: str, origin: tuple[float, float] | None, emit: Emit, component: str = "prbc") -> dict:
    """Live stock for one district and component. Never raises: on any failure returns cached data or
    an 'unavailable' result with suggest_donor_search=True, so the emergency flow never blocks."""
    from . import stock_history

    component = normalize_component(component)
    key = (state.lower(), district.lower(), component)
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        with session_scope() as db:
            cached = db.scalar(select(StockCache).where(StockCache.state == state, StockCache.district == district, StockCache.component == component))
            cache = None
            if cached:
                cache = {"results": cached.results, "fetched_at": cached.fetched_at, "source": cached.source,
                         "run_id": cached.source_run_id, "streaming_url": cached.streaming_url}
            directory = db.scalars(select(BloodBank)).all()
            db.expunge_all()

        fresh = cache and utcnow() - cache["fetched_at"] < timedelta(minutes=settings.stock_cache_ttl_min)
        mode = "live" if settings.tinyfish_live else "demo"
        if fresh and (cache["source"] == "demo") == (mode == "demo"):
            await emit({"type": "progress", "message": "Using results fetched in the last few minutes."})
            return _result("cache", cache["results"], cache["fetched_at"], cache["run_id"], cache["streaming_url"],
                           directory, origin, sample=mode == "demo", component=component, served_by="cache")

        if mode == "demo":
            await emit({"type": "progress", "message": "TinyFish key not set. Showing sample stock."})
            await asyncio.sleep(0.6)
            banks = _demo_banks(state, district, origin, component)
            _store(state, district, component, banks, "demo", None, None)
            return _result("demo", banks, utcnow(), None, None, directory, origin, sample=True, component=component, served_by="sample")

        # 1. replay the learned recipe on the Browser API (fast path)
        started = time.monotonic()
        await emit({"type": "progress", "message": "Replaying the saved eRaktKosh route on a TinyFish browser."})
        replayed = await _try_replay(state, district, component)
        if replayed:
            banks, meta = replayed
            secs = round(time.monotonic() - started, 1)
            _store(state, district, component, banks, "live", f"recipe-v{meta['recipe_version']}", None)
            stock_history.record(state, district, component, banks, "replay")
            ensure_verification(state, district, component, banks, meta["recipe_id"])
            out = _result("live", banks, utcnow(), f"recipe-v{meta['recipe_version']}", None, directory, origin, sample=False,
                          component=component, served_by="replay")
            out["duration_s"] = secs
            return out

        # 2. the Agent, which also re-learns the route
        await emit({"type": "progress", "message": "Saved route did not work. Sending the TinyFish agent instead."})
        # an Agent success after a failed replay saves a fresh recipe version (self-healing)
        healed = settings.tinyfish_replay_enabled and importlib.util.find_spec("playwright") is not None
        try:
            agent = await run_stock_agent(state, district, component, emit)
        except Exception as e:  # noqa: BLE001
            reason = "timeout" if isinstance(e, TimeoutError) else str(e)[:200]
            log.warning("tinyfish lookup %s/%s failed: %s", state, district, reason)
            if cache:
                out = _result("stale_cache", cache["results"], cache["fetched_at"], cache["run_id"], cache["streaming_url"],
                              directory, origin, sample=cache["source"] == "demo", component=component, served_by="stale_cache")
            else:
                out = {"source": "unavailable", "fetched_at": None, "banks": [], "run_id": getattr(e, "run_id", None),
                       "streaming_url": getattr(e, "streaming_url", None), "sample": False, "component": component,
                       "served_by": "none"}
            out["reason"] = reason
            out["suggest_donor_search"] = True
            return out
        learn_from_agent(state, district, component, agent["form_values"], agent["run_id"], healed=healed)
        _store(state, district, component, agent["banks"], "live", agent["run_id"], agent["streaming_url"])
        stock_history.record(state, district, component, agent["banks"], "agent")
        out = _result("live", agent["banks"], utcnow(), agent["run_id"], agent["streaming_url"], directory, origin,
                      sample=False, component=component, served_by="agent")
        out["duration_s"], out["steps"] = round(time.monotonic() - started, 1), agent["steps"]
        return out


_replays_since_verify = {"n": 0}
_background: set = set()


def ensure_verification(state, district, component, banks, recipe_id) -> None:
    """Every Nth replay, check it against an Agent run in the background (never on the family's critical path)."""
    _replays_since_verify["n"] += 1
    if settings.tinyfish_verify_every <= 0 or _replays_since_verify["n"] % settings.tinyfish_verify_every:
        return
    try:
        task = asyncio.get_running_loop().create_task(verify_replay(state, district, component, banks, recipe_id))
        _background.add(task)
        task.add_done_callback(_background.discard)
    except RuntimeError:
        pass


def _store(state, district, component, banks, source, run_id, streaming_url) -> None:
    clean = [{k: v for k, v in b.items() if k not in ("distance_km", "match_score")} for b in banks]
    with session_scope() as db:
        row = db.scalar(select(StockCache).where(StockCache.state == state, StockCache.district == district, StockCache.component == component))
        if row is None:
            row = StockCache(state=state, district=district, component=component)
            db.add(row)
        row.results, row.source, row.source_run_id, row.streaming_url, row.fetched_at = clean, source, run_id, streaming_url, utcnow()


def _result(source, banks, fetched_at, run_id, streaming_url, directory, origin, sample, component="prbc", served_by=None) -> dict:
    banks = attach_locations([dict(b) for b in banks], directory, origin)
    return {"source": source, "fetched_at": fetched_at, "banks": banks, "run_id": run_id, "streaming_url": streaming_url,
            "sample": sample, "component": component, "component_label": ERAKTKOSH_COMPONENT[component][0], "served_by": served_by}


# ---------------------------------------------------------------- Search (Verify)
async def search(query: str, purpose: str, **kw) -> list | None:
    """TinyFish Search; None in demo mode or on failure (callers treat None as 'could not check')."""
    if not settings.tinyfish_live:
        return None
    started = time.monotonic()
    try:
        async with asyncio.timeout(10):
            res = await _client(timeout=10).search.query(query, location="IN", language="en", **kw)
        record_run("search", purpose, "ok", started, query, source="web")
        return list(res.results)
    except Exception as e:  # noqa: BLE001
        record_run("search", purpose, "failed", started, query, error=str(e), source="web")
        log.info("search failed: %s", e)
        return None


def _tok(name: str) -> set[str]:
    stop = {"blood", "bank", "centre", "center", "hospital", "the", "of", "and", "govt", "government", "ltd", "pvt", "delhi", "new"}
    return {t for t in re.findall(r"[a-z]+", (name or "").lower()) if t not in stop and len(t) > 2}


async def verify_hospital(name: str, near: str = "", lat: float | None = None, lng: float | None = None) -> dict:
    """Hospital check with a score and evidence (W5). Never raises.
    Evidence comes from our eRaktKosh directory (always) and TinyFish Search (live mode):
    matched title, URL, address overlap, and the distance between the found place and the claimed point."""
    from .directory import similarity

    evidence: list[dict] = []
    words = _tok(name)
    with session_scope() as db:
        banks = db.scalars(select(BloodBank)).all()
        db.expunge_all()
    def near_factor(b) -> float:  # chains have many branches: prefer the one at the claimed spot
        return 1.0 if lat is None else 1.0 if haversine_km(lat, lng, b.lat, b.lng) <= 3 else 0.5
    cand = sorted(((min(1.0, similarity({"name": name, "address": near}, b)) * near_factor(b), b) for b in banks), key=lambda x: -x[0])[:1]
    dir_score = 0.0
    if cand and cand[0][0] >= 0.3:
        dir_score, b = cand[0]
        s = similarity({"name": name, "address": near}, b)
        dist = round(haversine_km(lat, lng, b.lat, b.lng), 1) if lat is not None else None
        evidence.append({"source": "eRaktKosh directory" if b.source == "eraktkosh" else "Rakt Doot directory",
                         "title": b.name, "url": "https://eraktkosh.mohfw.gov.in/BLDAHIMS/bloodbank/nearbyBBRed.cnt",
                         "distance_km": dist, "match": round(s, 2)})
    web_score = 0.0
    results = await search(f"{name} hospital {near}".strip(), "hospital_verify")
    if results:
        for r in results[:5]:
            hit = _tok(r.title + " " + r.snippet)
            overlap = len(words & hit) / max(1, len(words))
            if overlap >= 0.5:
                addr = _tok(near) & hit if near else set()
                web_score = max(web_score, min(1.0, overlap * 0.8 + (0.2 if addr else 0)))
                evidence.append({"source": "TinyFish Search", "title": r.title[:160], "url": r.url, "match": round(overlap, 2),
                                 "address_match": bool(addr)})
                if len(evidence) >= 3:
                    break
    score = round(max(dir_score, web_score), 2)
    if evidence:
        verified = score >= 0.6
    else:
        verified = None if results is None else False  # None = could not check the web (demo mode / Search down)
    return {"score": score, "verified": verified, "evidence": evidence,
            "checked_with": ["directory"] + (["search"] if results is not None else [])}


# ---------------------------------------------------------------- Fetch
async def fetch(urls: list[str], purpose: str, fmt: str = "markdown") -> dict[str, str]:
    """TinyFish Fetch, up to 10 URLs. {url: text}; empty dict in demo mode or on failure."""
    if not settings.tinyfish_live or not urls:
        return {}
    started = time.monotonic()
    try:
        async with asyncio.timeout(150):
            res = await _client(timeout=150).fetch.get_contents(urls[:10], purpose=purpose, format=fmt)
        record_run("fetch", purpose, "ok", started, urls[0], source="web")
        return {r.url: r.text or "" for r in res.results}
    except Exception as e:  # noqa: BLE001
        record_run("fetch", purpose, "failed", started, urls[0], error=str(e), source="web")
        log.info("fetch failed: %s", e)
        return {}


def fetch_sync(urls: list[str], purpose: str) -> dict[str, str]:
    """For scripts and admin actions running outside the event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(fetch(urls, purpose))
    raise RuntimeError("fetch_sync called inside an event loop; await fetch() instead")


# ---------------------------------------------------------------- Batch sweep (Sense, S1)
async def batch_sweep(targets: list[tuple[str, str]], component: str = "prbc", poll_s: float = 5, max_wait_s: float = 600) -> dict:
    """Queue one Agent run per (state, district) with POST /v1/automation/run-batch, poll the runs,
    and write every valid result to stock_cache + stock_history."""
    from . import stock_history

    component = normalize_component(component)
    if not settings.tinyfish_live:
        return {"mode": "demo", "queued": 0, "note": "Set TINYFISH_API_KEY to sweep live stock."}
    label = ERAKTKOSH_COMPONENT[component][0]
    runs = []
    for state, district in targets[:100]:
        run = {"url": settings.eraktkosh_stock_url, "goal": GOAL_TEMPLATE.format(state=state, district=district, component=label),
               "browser_profile": "stealth", "api_integration": "rakt-doot"}
        if _proxy_on():
            run["proxy_config"] = {"enabled": True, "country_code": settings.tinyfish_proxy_country.upper()}
        if settings.tinyfish_webhook_url:
            run["webhook_url"] = settings.tinyfish_webhook_url
        runs.append(run)
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.post(f"{AGENT_API}/v1/automation/run-batch", json={"runs": runs}, headers={"X-API-Key": settings.tinyfish_api_key})
        body = r.json() if r.content else {}
        if r.status_code >= 400 or body.get("error"):
            err = str(body.get("error") or r.text)[:200]
            record_run("batch", "stock_sweep", "failed", started, f"{len(runs)} districts", error=err)
            return {"queued": 0, "error": err}
    run_ids = body.get("run_ids") or []
    record_run("batch", "stock_sweep", "ok", started, f"{len(run_ids)} districts", run_id=(run_ids or [None])[0])
    pending = dict(zip(run_ids, targets))
    done = {"queued": len(run_ids), "stored": 0, "failed": 0}
    client = _client(timeout=30)
    deadline = time.monotonic() + max_wait_s
    while pending and time.monotonic() < deadline:
        await asyncio.sleep(poll_s)
        for rid in list(pending):
            try:
                run = await client.runs.get(rid)
            except Exception:  # noqa: BLE001
                continue
            if str(run.status) not in ("COMPLETED", "FAILED", "CANCELLED", "RunStatus.COMPLETED", "RunStatus.FAILED", "RunStatus.CANCELLED"):
                continue
            state, district = pending.pop(rid)
            banks, error = validate_result(run.result) if str(run.status).endswith("COMPLETED") else (None, "failed")
            if banks:
                _store(state, district, component, banks, "live", rid, None)
                done["stored"] += stock_history.record(state, district, component, banks, "batch")
            else:
                done["failed"] += 1
    done["timed_out"] = len(pending)
    return done


# ---------------------------------------------------------------- Monitor (Sense, S2)
async def create_monitor(kind: str, config: dict, cron: str, name: str, purpose: str) -> dict:
    """POST /v1/monitors. kind 'fetch' (Page) or 'search' (Topic). Scheduled results go to the webhook."""
    if not settings.tinyfish_live:
        return {"mode": "demo", "created": False}
    body = {"type": kind, "name": name, "config": config, "schedule_cron": cron, "purpose": purpose}
    if settings.tinyfish_webhook_url:
        from urllib.parse import urlsplit, urlunsplit
        u = urlsplit(settings.tinyfish_webhook_url)  # keep ?key=... on the monitor URL
        body["webhook_url"] = urlunsplit(u._replace(path=u.path.rstrip("/") + "/monitor"))
    started = time.monotonic()
    async with httpx.AsyncClient(timeout=60) as http:
        r = await http.post(f"{AGENT_API}/v1/monitors", json=body, headers={"X-API-Key": settings.tinyfish_api_key})
    ok = r.status_code < 400
    record_run("monitor", f"monitor:{kind}", "ok" if ok else "failed", started, name, error=None if ok else r.text[:200], source="web")
    return {"created": ok, "status": r.status_code, "body": r.json() if ok and r.content else r.text[:300]}
