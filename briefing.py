"""
On-demand AI risk briefings (daily, weekly, monthly, quarterly).

Works with no API key: the briefing is assembled from the classified data.
If OPENAI_API_KEY is set (e.g. in .env), an executive summary paragraph is
added by an LLM on top of the same facts.

CLI:
    python briefing.py --period weekly
    python briefing.py --period quarterly --as-of 2026-06-30 > briefing.md
"""
import argparse
import os
from datetime import date, timedelta

import pandas as pd

import frameworks as fw
import llm

PERIODS = ["daily", "weekly", "monthly", "quarterly"]
HIGH_TIERS = ["Unacceptable (Art. 5)", "High-risk (Annex I/III)"]


def load(path="data/incidents_classified.csv"):
    df = pd.read_csv(path, parse_dates=["date"])
    return df.fillna({"description": "", "url": "", "aiid_id": "", "responsible_company": "", "responsible_entities": "",
                      "alleged_deployer": "", "alleged_developer": "", "harmed_parties": "", "mit_risk_domain": "",
                      "mit_intent": "", "also_reported_by": ""})


def period_window(period, as_of):
    """Return (start, end) inclusive for the period that contains as_of."""
    as_of = pd.Timestamp(as_of).normalize()
    if period == "daily":
        start = as_of
    elif period == "weekly":
        start = as_of - timedelta(days=as_of.weekday())  # Monday
    elif period == "monthly":
        start = as_of.replace(day=1)
    elif period == "quarterly":
        start = as_of.replace(month=3 * ((as_of.month - 1) // 3) + 1, day=1)
    else:
        raise ValueError(f"period must be one of {PERIODS}")
    end = {
        "daily": start,
        "weekly": start + timedelta(days=6),
        "monthly": start + pd.offsets.MonthEnd(0),
        "quarterly": start + pd.offsets.QuarterEnd(0),
    }[period]
    return start, pd.Timestamp(end)


def previous_window(period, start):
    return period_window(period, start - timedelta(days=1))


def eligible(df, period):
    """Daily/weekly need day-precise dates; monthly/quarterly also accept month-precise."""
    ok = ["day"] if period in ("daily", "weekly") else ["day", "month"]
    return df[df["date_precision"].isin(ok)]


def latest_date(df, period=None):
    """Latest day-precise date, so every period lines up on the same 'as of' day."""
    return df.loc[df["date_precision"] == "day", "date"].max()


def slice_period(df, period, as_of):
    d = eligible(df, period)
    start, end = period_window(period, as_of)
    pstart, pend = previous_window(period, start)
    cur = d[(d["date"] >= start) & (d["date"] <= end)]
    prev = d[(d["date"] >= pstart) & (d["date"] <= pend)]
    return cur, prev, (start, end), (pstart, pend)


def pct_change(cur, prev):
    if prev == 0:
        return "new" if cur else "flat"
    ch = (cur - prev) / prev * 100
    return f"{ch:+.0f}%"


def count_table(cur, prev, col, top=None):
    c = cur[col].value_counts()
    p = prev[col].value_counts()
    rows = []
    for k, v in (c.head(top) if top else c).items():
        rows.append((k, int(v), int(p.get(k, 0)), pct_change(v, p.get(k, 0))))
    return rows


def explode_controls(df):
    s = df["iso42001_controls"].str.split("; ").explode()
    return s[s.notna() & (s != "")]


def build_stats(df, period, as_of=None):
    as_of = pd.Timestamp(as_of) if as_of else latest_date(df, period)
    cur, prev, (start, end), (pstart, pend) = slice_period(df, period, as_of)
    iso_cur = explode_controls(cur).value_counts()
    iso_prev = explode_controls(prev).value_counts()
    harm_delta = (
        cur["harm_type"].value_counts().subtract(prev["harm_type"].value_counts(), fill_value=0).sort_values(ascending=False)
    )
    return {
        "period": period,
        "data_through": latest_date(df).date(),
        "start": start.date(),
        "end": end.date(),
        "prev_start": pstart.date(),
        "prev_end": pend.date(),
        "total": len(cur),
        "prev_total": len(prev),
        "high": int(cur["eu_ai_act_tier"].isin(HIGH_TIERS).sum()),
        "prev_high": int(prev["eu_ai_act_tier"].isin(HIGH_TIERS).sum()),
        "critical": int((cur["severity"] == "Critical").sum()),
        "avg_risk": round(cur["risk_score"].mean(), 1) if len(cur) else 0,
        "tiers": count_table(cur, prev, "eu_ai_act_tier"),
        "harms": count_table(cur, prev, "harm_type", top=6),
        "nist": count_table(cur, prev, "nist_characteristic"),
        "nist_fn": count_table(cur, prev, "nist_function"),
        "iso": [(k, fw.ISO_CONTROLS[k], int(v), int(iso_prev.get(k, 0))) for k, v in iso_cur.head(6).items()],
        "rising": [(k, int(v)) for k, v in harm_delta.items() if v > 0 and k != "Other"][:3],
        "top": cur[(cur["harm_type"] != "Other") & (cur["story_type"] != "Positive use / benefit")].sort_values("risk_score", ascending=False).head(5),
        "sectors": cur.loc[cur["sector"] != "Unknown", "sector"].value_counts().head(3),
        "companies": cur.loc[cur["responsible_company"].fillna("") != "", "responsible_company"].value_counts().head(5),
    }


def md_table(header, rows):
    out = "| " + " | ".join(header) + " |\n|" + "---|" * len(header) + "\n"
    for r in rows:
        out += "| " + " | ".join(str(x) for x in r) + " |\n"
    return out


def render(stats, exec_summary=None):
    s = stats
    title = f"# AI Risk Briefing — {s['period'].title()}\n"
    sub = f"**Period:** {s['start']} to {s['end']}  ·  **Compared with:** {s['prev_start']} to {s['prev_end']}  ·  **Data current through:** {s['data_through']}\n\n"
    if s["total"] == 0:
        return title + sub + "No incidents with a precise enough date fall in this period. Try a longer period or an earlier date.\n"

    lines = [title, sub]
    if s["end"] > s["data_through"]:
        lines.append(f"> **Partial period:** data runs only through {s['data_through']}, so comparisons with the full prior period understate activity.\n\n")
    if exec_summary:
        lines += ["## Executive summary\n", exec_summary.strip() + "\n\n"]

    lines += [
        "## Headline\n",
        f"- **{s['total']} incident{'s' if s['total'] != 1 else ''}** logged ({pct_change(s['total'], s['prev_total'])} vs prior period, {s['prev_total']} before).\n",
        f"- **{s['high']}** fall in EU AI Act *unacceptable* or *high-risk* territory ({pct_change(s['high'], s['prev_high'])}).\n",
        f"- **{s['critical']}** rated Critical severity; average risk score **{s['avg_risk']}/100**.\n",
    ]
    if len(s["sectors"]):
        lines.append("- Most affected sectors: " + ", ".join(f"{k} ({v})" for k, v in s["sectors"].items()) + ".\n")
    if len(s["companies"]):
        lines.append("- Most-cited companies (alleged developer/deployer): " + ", ".join(f"{k} ({v})" for k, v in s["companies"].items()) + ".\n")
    if s["rising"]:
        lines.append("- Rising fastest: " + ", ".join(f"{k} (+{v})" for k, v in s["rising"]) + ".\n")

    lines += ["\n## EU AI Act risk tiers\n", md_table(["Tier", "Now", "Prior", "Change"], s["tiers"])]
    lines += ["\n## Harm types\n", md_table(["Harm type", "Now", "Prior", "Change"], s["harms"])]
    lines += ["\n## NIST AI RMF\n", "**Trustworthiness characteristic at stake**\n\n",
              md_table(["Characteristic", "Now", "Prior", "Change"], s["nist"]),
              "\n**Core function most implicated**\n\n",
              md_table(["Function", "Now", "Prior", "Change"], s["nist_fn"])]
    lines += ["\n## ISO/IEC 42001 Annex A controls implicated\n",
              md_table(["Control", "Objective", "Incidents", "Prior"], s["iso"])]

    lines.append("\n## Highest-risk incidents\n")
    for _, r in s["top"].iterrows():
        link = f" ([source]({r['url']}))" if r["url"] else ""
        lines.append(
            f"- **{r['title']}** — {r['date']:%Y-%m-%d}, {r['severity']}, risk {r['risk_score']}{link}\n"
            + (f"  - Alleged responsible party: {r['responsible_company']}\n" if r["responsible_company"] else "")
            +
            f"  - EU AI Act: {r['eu_ai_act_tier']} · {r['eu_ai_act_basis']}\n"
            f"  - NIST: {r['nist_characteristic']} ({r['nist_function']}) · ISO 42001: {r['iso42001_primary']} {r['iso42001_primary_name']}\n"
        )

    lines.append("\n## Recommended actions\n")
    for k, name, _, _ in s["iso"][:3]:
        lines.append(f"1. **{k} {name}:** {fw.ISO_ACTIONS[k]}\n")
    lines.append(
        "\n---\n*Classifications are indicative keyword-rule mappings for triage, not legal determinations. "
        "Data: AI Incident Database (incidentdatabase.ai), AIAAIC Repository, OECD AI Incidents Monitor and MIT AI Risk Repository, via the GenAI & Agentic AI Incidents corpus.*\n"
    )
    return "".join(lines)


def llm_provider():
    return llm.provider()


def llm_summary(markdown):
    """Optional 3-4 sentence executive summary."""
    return llm.chat(
        "You are an AI governance analyst. Write a 3-4 sentence executive summary for a risk committee. "
        "Use only facts in the briefing. Name the EU AI Act, NIST AI RMF and ISO/IEC 42001 implications. No preamble.",
        markdown,
    )


def generate(df, period, as_of=None, use_llm=False):
    stats = build_stats(df, period, as_of)
    md = render(stats)
    if use_llm and stats["total"]:
        summary = llm_summary(md)
        if summary:
            md = render(stats, summary)
    return md, stats


if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--period", choices=PERIODS, default="weekly")
    ap.add_argument("--as-of", help="YYYY-MM-DD; defaults to the latest date in the data")
    ap.add_argument("--llm", action="store_true", help="add an AI executive summary (OpenAI or Groq key)")
    a = ap.parse_args()
    print(generate(load(), a.period, a.as_of, a.llm)[0])
