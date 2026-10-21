"""'Agent learns, Browser replays' (Section 2.4).

The TinyFish Agent is flexible but slow (30-60 s). Once it has found its way through eRaktKosh's
Stock Availability form, the same lookup can be replayed deterministically on the TinyFish
Browser API (a remote Chrome over CDP, driven by Playwright) in a few seconds.

A recipe is data, not code: a list of steps run by `execute()` against a Playwright page.
The step template mirrors what the page itself does when you press Search (it loads the
district list, then the stock table from the site's own XHR endpoints, inside the site's
origin and session). What the Agent *learns* is the part that drifts: the option values for
state, district and component, which it reports in its structured output after every
successful run. When a replay fails (layout or code change, empty or invalid result), the
caller falls back to the Agent, which re-learns those values and saves a new recipe version.

Recipes run inside a warm browser session that is reused for a few minutes, because creating a
session costs 10-30 s."""
import asyncio
import json
import logging
import time
from typing import Any, Protocol

from ..config import settings
from ..core.compatibility import ERAKTKOSH_COMPONENT
from . import eraktkosh

log = logging.getLogger("raktdoot.replay")
SITE = "eraktkosh_stock"
FAILS_BEFORE_RETIRE = 3

# The step template. Values in {braces} come from the lookup and from what the Agent learned.
DEFAULT_STEPS: list[dict] = [
    {"op": "goto", "url": eraktkosh.STOCK_PAGE},
    {"op": "xhr", "url": "/BLDAHIMS/bloodbank/nearbyBB.cnt?hmode=GETDISTRICTLIST&selectedStateCode={state_code}", "save": "districts"},
    {"op": "pick_district", "from": "districts"},
    {"op": "xhr", "url": "/BLDAHIMS/bloodbank/nearbyBB.cnt?hmode=GETNEARBYSTOCKDETAILS&stateCode={state_code}"
                         "&districtCode={district_code}&bloodGroup=all&bloodComponent={component_code}&lang=0", "save": "stock"},
    {"op": "parse", "parser": "eraktkosh_stock_rows", "from": "stock"},
]

FETCH_JS = """async (u) => {
  const r = await fetch(u, {headers: {"X-Requested-With": "XMLHttpRequest"}, credentials: "same-origin"});
  if (!r.ok) throw new Error("HTTP " + r.status);
  return await r.text();
}"""


class ReplayError(RuntimeError):
    pass


class Page(Protocol):
    async def goto(self, url: str, **kw) -> Any: ...
    async def evaluate(self, expression: str, arg: Any = None) -> Any: ...


def variables(learned: dict, state: str, district: str, component: str) -> dict:
    """Option codes for this lookup: learned by the Agent first, our static tables second."""
    learned = learned or {}
    st = learned.get("states", {}).get(state) or eraktkosh.state_code(state)
    comp = learned.get("components", {}).get(component) or ERAKTKOSH_COMPONENT[component][1]
    if not st:
        raise ReplayError(f"no state code for {state!r}")
    return {"state": state, "district": district, "state_code": st, "component_code": comp,
            "district_code": learned.get("districts", {}).get(f"{state}/{district}")}


async def execute(page: Page, steps: list[dict], vars_: dict) -> list[dict]:
    """Run recipe steps on a page. Raises ReplayError on anything unexpected; never guesses."""
    saved: dict[str, Any] = {}
    banks: list[dict] | None = None
    for step in steps:
        op = step.get("op")
        if op == "goto":
            await page.goto(step["url"].format(**vars_), wait_until="domcontentloaded", timeout=20000)
        elif op == "xhr":
            text = await page.evaluate(FETCH_JS, step["url"].format(**vars_))
            try:
                saved[step["save"]] = json.loads(text[text.find("{"):] if isinstance(text, str) else text)
            except (ValueError, TypeError):
                raise ReplayError(f"{step['save']}: response was not JSON (layout changed?)")
        elif op == "pick_district":
            records = (saved.get(step["from"]) or {}).get("records") or []
            code = eraktkosh.match_district(vars_["district"], records)
            if code is None and vars_.get("district_code") in {str(r.get("value")) for r in records}:
                code = vars_["district_code"]
            if code is None:
                raise ReplayError(f"district {vars_['district']!r} not in the site's list")
            vars_["district_code"] = code
        elif op == "parse":
            payload = saved.get(step["from"])
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ReplayError("stock payload has no data table")
            banks = eraktkosh.parse_stock_rows(payload)
            if payload["data"] and not banks:
                raise ReplayError("rows present but none parsed (columns changed?)")
        else:
            raise ReplayError(f"unknown step {op!r}")
    if banks is None:
        raise ReplayError("recipe has no parse step")
    return banks


# ---------------------------------------------------------------- warm Browser API session
_session: dict = {}
_session_lock = asyncio.Lock()
SESSION_REUSE_S = 240


async def _new_session():
    from tinyfish import AsyncTinyFish, BrowserProxyConfig

    client = AsyncTinyFish(api_key=settings.tinyfish_api_key, timeout=60)
    proxy = BrowserProxyConfig(country_code=settings.tinyfish_proxy_country) if _proxy_on() else None
    return await client.browser.sessions.create(url=eraktkosh.STOCK_PAGE, timeout_seconds=SESSION_REUSE_S + 60, proxy_config=proxy)


def _proxy_on() -> bool:
    return settings.tinyfish_proxy_country.lower() not in ("", "off", "none")


async def run(steps: list[dict], learned: dict, state: str, district: str, component: str) -> tuple[list[dict], dict]:
    """Replay on the TinyFish Browser API. Returns (banks, meta). Raises on any failure."""
    from playwright.async_api import async_playwright

    vars_ = variables(learned, state, district, component)
    started = time.monotonic()
    async with _session_lock:
        fresh = not _session or time.monotonic() - _session["at"] > SESSION_REUSE_S
        if fresh:
            s = await _new_session()
            _session.update(id=s.session_id, cdp=s.cdp_url, at=time.monotonic())
        cdp, sid = _session["cdp"], _session["id"]
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.connect_over_cdp(cdp, timeout=20000)
            ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            banks = await execute(page, steps, vars_)
    except Exception:
        _session.clear()  # a broken session is not reused
        raise
    return banks, {"session_id": sid, "warm": not fresh, "duration_ms": int((time.monotonic() - started) * 1000),
                   "district_code": vars_["district_code"]}
