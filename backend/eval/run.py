"""Rakt Doot AI benchmark (F8). One command reproduces every number in docs/eval_results.md.

    cd backend
    python -m eval.run                 # offline: rules / sample / synthetic numbers, no keys needed
    python -m eval.run --live          # also the LLM, vision, live Search (uses keys from .env)
    python -m eval.run --live --tinyfish 5   # + 5 live stock lookups per path (Agent vs replay); costs credits

Runs against a throwaway SQLite database seeded like a fresh clone, never your real one."""
import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(__file__).resolve().parent / "data"
OUT = ROOT.parent / "docs" / "eval_results.md"


def configure(live: bool) -> None:
    os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/eval.db"
    os.environ["WHATSAPP_MODE"] = "mock"
    os.environ["RESPECT_QUIET_HOURS"] = "false"
    os.environ["FORECAST_ENABLED"] = "true"
    if not live:
        for k in ("TINYFISH_API_KEY", "LLM_API_KEY", "STT_API_KEY"):
            os.environ[k] = ""
        os.environ["TINYFISH_MODE"] = "demo"
        os.environ["GEOCODER"] = "off"
    sys.path.insert(0, str(ROOT))


def prf(pairs: list[tuple[str, str]], labels: list[str]) -> dict:
    out = {}
    for lab in labels:
        tp = sum(1 for g, p in pairs if g == lab and p == lab)
        fp = sum(1 for g, p in pairs if g != lab and p == lab)
        fn = sum(1 for g, p in pairs if g == lab and p != lab)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        out[lab] = {"precision": round(prec, 3), "recall": round(rec, 3), "f1": round(2 * prec * rec / (prec + rec), 3) if prec + rec else 0.0,
                    "support": sum(1 for g, _ in pairs if g == lab)}
    return out


def table(rows: list[list], head: list[str]) -> str:
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join(" --- " for _ in head) + "|"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


# ---------------------------------------------------------------- 1. intent parsing
def eval_intents(use_llm: bool) -> tuple[str, dict]:
    from app.services.llm import parse_intent, rule_parse

    rows = [json.loads(line) for line in (DATA / "intents.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    labels = sorted({r["intent"] for r in rows})
    engines = {"rules": lambda r: rule_parse(r["text"], r.get("pending"))}
    if use_llm:
        def llm(r):
            ctx = "Donor has accepted and is heading to the hospital." if r.get("context") == "connected" else \
                "Donor received an emergency blood alert and has not replied yet."
            return parse_intent(r["text"], f"Donor is answering: {r['pending']}" if r.get("pending") else ctx, r.get("pending"))
        engines["llm"] = llm
    md, metrics = [], {}
    for name, fn in engines.items():
        pairs, per_lang, slots_ok, slots_n = [], defaultdict(list), 0, 0
        t0 = time.perf_counter()
        for r in rows:
            out = fn(r)
            pred = out["intent"] if out["confidence"] >= 0.7 else "unknown"
            pairs.append((r["intent"], pred))
            per_lang[r["lang"]].append(r["intent"] == pred)
            if "answer" in r:
                slots_n += 1
                slots_ok += out.get("eligibility_answer") is r["answer"] and pred == "eligibility_answer"
        ms = (time.perf_counter() - t0) * 1000 / len(rows)
        acc = sum(g == p for g, p in pairs) / len(pairs)
        f1 = prf(pairs, labels)
        metrics[name] = {"accuracy": round(acc, 3), "macro_f1": round(statistics.mean(v["f1"] for v in f1.values()), 3)}
        md.append(f"**{name}**: accuracy **{acc:.1%}**, macro-F1 {metrics[name]['macro_f1']:.3f}, "
                  f"eligibility yes/no correct {slots_ok}/{slots_n}, {ms:.1f} ms per message. "
                  + ", ".join(f"{k}: {sum(v) / len(v):.0%}" for k, v in sorted(per_lang.items())))
        md.append(table([[lab, v["precision"], v["recall"], v["f1"], v["support"]] for lab, v in f1.items()],
                        ["intent", "precision", "recall", "F1", "n"]))
        cm = Counter(pairs)
        md.append("<details><summary>Confusion matrix (" + name + ")</summary>\n\n" +
                  table([[g] + [cm[(g, p)] or "" for p in labels] for g in labels], ["gold \\ predicted"] + labels) + "\n\n</details>")
    return f"{len(rows)} labelled donor replies (English, Hindi in Devanagari, Hinglish).\n\n" + "\n\n".join(md), metrics


# ---------------------------------------------------------------- 2. slips (F3)
def eval_slips() -> tuple[str, dict]:
    from app.services import vision

    gold = json.loads((DATA / "slips.json").read_text(encoding="utf-8"))
    fields = ["patient_group", "units", "component", "hospital", "ward", "urgency", "date"]
    correct, total, engine = Counter(), Counter(), set()
    for g in gold:
        out = vision.parse_slip(vision.sample_bytes(g["file"]) or b"")
        engine.add(out.get("engine", "error"))
        got = out.get("fields") or {}
        for f in fields:
            total[f] += 1
            a, b = str(got.get(f) or "").lower(), str(g["fields"][f]).lower()
            correct[f] += (a == b) or (f in ("hospital", "ward") and a and (a in b or b in a))
    acc = sum(correct.values()) / sum(total.values())
    note = ("Demo mode: the bundled sample slips return their stored parse, so this only checks the pipeline, "
            "not a model." if engine == {"sample"} else f"Engine: {', '.join(sorted(engine))}.")
    return (f"{len(gold)} synthetic requisition slips (handwriting-style font, slight rotation and blur). {note}\n\n" +
            table([[f, f"{correct[f]}/{total[f]}"] for f in fields] + [["**all fields**", f"**{acc:.1%}**"]], ["field", "correct"])), \
        {"field_accuracy": round(acc, 3), "engine": sorted(engine)}


# ---------------------------------------------------------------- 3. forward checker (F2)
def eval_forwards() -> tuple[str, dict]:
    from app.db import SessionLocal
    from app.models import Request
    from app.services import forwards

    today = date.today()
    fill = {"{today}": today.strftime("%d/%m/%Y")}
    for n in (6, 8, 9, 11, 14, 20, 30, 45):
        fill[f"{{days_ago_{n}}}"] = (today - timedelta(days=n)).strftime("%d/%m/%Y")
    rows = [json.loads(line) for line in (DATA / "forwards.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    pairs = []
    with SessionLocal() as db:
        db.add(Request(patient_group="B+", units=1, patient_age=40, patient_gender="M", hospital_name="Max Super Speciality Hospital, Saket",
                       hospital_lat=28.5276, hospital_lng=77.2117, requester_name="Eval", requester_phone="919876543210", status="fulfilled"))
        db.commit()
        for r in rows:
            text = r["text"]
            for k, v in fill.items():
                text = text.replace(k, v)
            pairs.append((r["label"], forwards.check(db, text, "eval")["verdict"]))
        db.rollback()
    labels = ["looks_genuine", "likely_stale", "likely_fulfilled", "unverified", "possible_scam"]
    res = prf(pairs, labels)
    acc = sum(g == p for g, p in pairs) / len(pairs)
    cm = Counter(pairs)
    return (f"{len(rows)} labelled pleas. Accuracy **{acc:.1%}**.\n\n" +
            table([[lab, v["precision"], v["recall"], v["f1"], v["support"]] for lab, v in res.items()], ["verdict", "precision", "recall", "F1", "n"]) +
            "\n\n<details><summary>Confusion matrix</summary>\n\n" +
            table([[g] + [cm[(g, p)] or "" for p in labels] for g in labels], ["gold \\ predicted"] + labels) + "\n\n</details>"), \
        {"accuracy": round(acc, 3), "scam_recall": res["possible_scam"]["recall"], "scam_precision": res["possible_scam"]["precision"]}


# ---------------------------------------------------------------- 4. forecast (F1)
def eval_forecast() -> tuple[str, dict]:
    from app.db import SessionLocal
    from app.services import forecast

    out = {}
    with SessionLocal() as db:
        for comp in ("prbc", "platelets"):
            out[comp] = forecast.backtest(db, comp)
        db.commit()
    rows = [[c, m["points"], m["mae"], m["naive_mae"], m["precision"], m["recall"], m["naive_precision"], m["naive_recall"],
             "synthetic" if m["synthetic"] else "real"] for c, m in out.items()]
    return ("Rolling-origin backtest over the last 30 days of every (district, group) series, forecasting 1-3 days ahead. "
            "Shortage = district total below the threshold within 72 h. Baseline = 'tomorrow looks like today'.\n\n" +
            table(rows, ["component", "forecasts", "MAE (units)", "naive MAE", "shortage precision", "shortage recall",
                         "naive precision", "naive recall", "data"]) +
            "\n\n**The history is SYNTHETIC** until real stock_history accumulates (14+ days per series); these numbers prove the "
            "pipeline, not real-world accuracy."), out


# ---------------------------------------------------------------- 5. family guide (F13)
def eval_guide() -> tuple[str, dict]:
    from app.db import SessionLocal
    from app.services import guide

    qs = json.loads((DATA / "guide_questions.json").read_text(encoding="utf-8"))
    with SessionLocal() as db:
        guide.ensure_loaded(db)
        db.commit()
    rows, ok_cite, ok_refuse, right_src = [], 0, 0, 0
    for q in qs:
        a = guide.answer(q["q"], q.get("lang", "en"))
        if q["answerable"]:
            cited = bool(a["sources"]) and not a["refused"]
            src = cited and any(q["expect_source"] in s["url"] for s in a["sources"])
            ok_cite += cited
            right_src += src
            rows.append([q["q"][:60], "answer", "cited" if cited else "NOT cited", "yes" if src else "no"])
        else:
            ok_refuse += a["refused"]
            rows.append([q["q"][:60], "refuse", "refused" if a["refused"] else "ANSWERED", "-"])
    n_ans = sum(1 for q in qs if q["answerable"])
    n_ref = len(qs) - n_ans
    return (f"{len(qs)} questions: {n_ans} answerable from the official sources, {n_ref} out of scope. "
            f"Answers with a citation: **{ok_cite}/{n_ans}**, citing the expected document: **{right_src}/{n_ans}**, "
            f"out-of-scope refused: **{ok_refuse}/{n_ref}**.\n\n" + table(rows, ["question", "expected", "result", "right source"])), \
        {"cited": ok_cite, "answerable": n_ans, "right_source": right_src, "refused": ok_refuse, "out_of_scope": n_ref}


# ---------------------------------------------------------------- 6. TinyFish (2.4)
def eval_tinyfish(n: int) -> tuple[str, dict]:
    import asyncio

    from app.config import settings
    from app.services import tinyfish_client

    if not settings.tinyfish_live or n <= 0:
        return ("Not measured in this run (needs `--live --tinyfish N` and TINYFISH_API_KEY; live runs cost credits). "
                "The replay and healing paths are covered by tests with recorded responses (tests/test_upgrade.py)."), {}

    async def quiet(_):
        return None
    results = {"agent": [], "replay": []}
    targets = [x.split("/", 1) for x in settings.stock_sweep_districts][:n]
    for path in ("agent", "replay"):
        settings.tinyfish_replay_enabled = path == "replay"
        for state, district in targets:
            t = time.perf_counter()
            tinyfish_client._store(state, district, "prbc", [], "demo", None, None)  # bust the cache
            out = asyncio.run(tinyfish_client.lookup_stock(state, district, None, quiet, "prbc"))
            results[path].append((out.get("served_by") == path and bool(out["banks"]), time.perf_counter() - t))
    rows = [[p, f"{sum(ok for ok, _ in r)}/{len(r)}", f"{statistics.median(s for _, s in r):.1f} s" if r else "-"] for p, r in results.items()]
    return table(rows, ["path", "successful", "median latency"]), {p: r for p, r in results.items()}


# ---------------------------------------------------------------- 7. bandit + ranker
def eval_bandit() -> tuple[str, dict]:
    from app.db import SessionLocal
    from app.models import BanditArm
    from app.services import bandit

    wins, shares = 0, []
    for seed in range(20):
        with SessionLocal() as db:
            db.query(BanditArm).filter_by(simulated=True).delete()
            out = bandit.simulate(db, n=800, seed=seed, seg=f"eval{seed}")
            wins += out["chosen_most"] == out["true_best"]
            shares.append(out["pulls"][out["true_best"]] / 800)
            db.rollback()
    rate = bandit.SIM_TRUE_RATES
    best, avg = max(rate.values()), statistics.mean(rate.values())
    exp_bandit = statistics.mean(s * best + (1 - s) * (avg * 5 - best) / 4 for s in shares)
    return (f"Simulated donors with hidden acceptance rates {rate} (labelled simulation). Over 20 runs of 800 alerts, "
            f"Thompson sampling sent the best wording most often in **{wins}/20** runs, giving it {statistics.mean(shares):.0%} of alerts on "
            f"average. Expected acceptance ≈ {exp_bandit:.1%} vs {avg:.1%} for a uniform random wording."), {"wins": wins}


def eval_ranker() -> tuple[str, dict]:
    sys.path.insert(0, str(ROOT / "scripts"))
    import random

    from train_ranker import KEYS, auc, synthetic_logs, train

    from app.core.ranking import score
    rows = synthetic_logs(3000)
    random.Random(1).shuffle(rows)
    tr, te = rows[:2400], rows[2400:]
    w, b = train(tr)
    labels = [y for _, y in te]
    h = auc([score(f) for f, _ in te], labels)
    lr = auc([sum(wi * f[k] for wi, k in zip(w, KEYS)) + b for f, _ in te], labels)
    return f"On 3,000 synthetic notification logs: heuristic AUC **{h:.3f}**, logistic regression AUC **{lr:.3f}** (synthetic; pipeline proof).", \
        {"heuristic_auc": round(h, 3), "lr_auc": round(lr, 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--tinyfish", type=int, default=0)
    args = ap.parse_args()
    configure(args.live)
    from app.config import settings
    from app.db import SessionLocal, init_db
    from app.seed import reset_and_seed

    init_db()
    with SessionLocal() as db:
        reset_and_seed(db, 200)
    from eval import intel_bench

    sections = [
        ("1. Intent parsing (donor replies)", lambda: eval_intents(bool(settings.llm_api_key))),
        ("2. Requisition slip parsing (F3)", eval_slips),
        ("3. Forward Checker (F2)", eval_forwards),
        ("4. Shortage forecast backtest (F1)", eval_forecast),
        ("5. Family guide (F13)", eval_guide),
        ("6. TinyFish: Agent vs replay (Section 2.4)", lambda: eval_tinyfish(args.tinyfish)),
        ("7. Message bandit (F11)", eval_bandit),
        ("8. Donor ranker", eval_ranker),
        ("9. Intel oneAPI: scikit-learn vs Intel Extension for Scikit-learn (F14)", intel_bench.run),
    ]
    mode = "live keys" if args.live else "offline (no keys: rules, sample and synthetic data)"
    md = [f"# Rakt Doot AI benchmark\n\nGenerated by `python -m eval.run{' --live' if args.live else ''}` on {date.today().isoformat()}, mode: **{mode}**.\n"]
    summary = {}
    for title, fn in sections:
        t = time.perf_counter()
        body, metrics = fn()
        summary[title] = metrics
        md.append(f"## {title}\n\n{body}\n")
        print(f"{title}: {json.dumps(metrics, default=str)[:300]}  ({time.perf_counter() - t:.1f} s)")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
