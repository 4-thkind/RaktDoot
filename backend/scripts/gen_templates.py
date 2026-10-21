"""Regenerate docs/whatsapp-templates.md from app/services/messages.py.

    python scripts/gen_templates.py"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.messages import BUTTONS, TEMPLATES, TEXT  # noqa: E402

QUICK = {
    "alert": ["can_donate", "not_today"], "alert_urgent": ["can_donate", "not_today"], "alert_distance": ["can_donate", "not_today"],
    "alert_why_you": ["can_donate", "not_today"], "alert_short": ["can_donate", "not_today"], "drive_alert": ["can_donate", "not_today"],
    "followup": ["donated", "deferred", "couldnt_go"], "onway": ["on_my_way", "cant_make_it"], "recurring_reminder": ["confirm", "cant"], "eligible_again_camp": ["register_me"],
}

HEAD = """# WhatsApp message templates

Business-initiated messages (outside the 24-hour window opened by a donor's reply) must use templates approved in Meta Business Manager. Register each one below under the **Utility** category, in English (`en`) and Hindi (`hi`), with the body exactly as shown. `{{1}}`, `{{2}}` ... are filled in this order by `app/services/whatsapp.py`.

Templates marked with quick replies need the buttons added as Quick Reply buttons; the backend attaches a payload to each at send time.

**Alert wording variants (message bandit, F11).** `blood_request_alert_v2`, `blood_alert_urgent`, `blood_alert_distance`, `blood_alert_why_you` and `blood_alert_short` are separate templates, because WhatsApp only allows a fixed, pre-approved body outside the 24-hour window. Register all five; until a variant is approved, set `BANDIT_ENABLED=false` so only the standard alert is used. Inside the 24-hour window the same text is sent as a normal message. The why-you line (`{{1}}` of `blood_alert_why_you`) is a variable, so it can change per donor without re-approval.

`blood_request_alert_v2` replaces the old `blood_request_alert`: it adds the component (red cells, platelets, plasma, whole blood) as `{{2}}`.

Generated from `backend/app/services/messages.py` by `python scripts/gen_templates.py`. Regenerate if you change the copy.
"""


def body(text: str, order: list[str]) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: "{{%d}}" % (order.index(m.group(1)) + 1), text)


if __name__ == "__main__":
    out = [HEAD]
    for key, (name, order) in TEMPLATES.items():
        out.append(f"## `{name}`\n")
        for lang in ("en", "hi"):
            out.append(f"**{lang}**\n\n```\n{body(TEXT[key][lang], order)}\n```\n")
        out.append("Variables: " + ", ".join(f"`{{{{{i}}}}}` {k}" for i, k in enumerate(order, 1)) + "\n")
        if key in QUICK:
            out.append("Quick replies: " + ", ".join(BUTTONS[b]["en"] for b in QUICK[key]) + "\n")
    path = Path(__file__).resolve().parents[2] / "docs" / "whatsapp-templates.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"wrote {len(TEMPLATES)} templates to {path}")
