"""
Load the AI Incident Database (AIID) snapshot (incidentdatabase.ai, CC BY-SA 4.0).

Gives each AIID incident its full description, the alleged deployer, developer
and harmed parties as separate fields, the MIT AI Risk Repository classification,
and the number and titles of news reports linked to it.

Expected files in data/raw/aiid/ (from the AIID "Download Complete Database" snapshot):
    incidents.csv, classifications_MIT.csv, duplicates.csv, report_titles.csv (optional)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

import companies as co

RAW = Path(__file__).parent / "data" / "raw" / "aiid"

# Common first names: an unmatched two/three-word entity starting with one is treated as a person
FIRST_NAMES = set("""
aaron adam alan albert alex alexander alice amanda amy andrew angela ann anna anthony arthur barbara ben benjamin bill bob brandon brian
carl carlos carol catherine charles chris christopher daniel david dennis diana donald douglas edward elizabeth elon emily emma eric
frank gary george gregory hannah harry helen henry jack james jane janet jason jeff jeffrey jennifer jessica jim joe john jonathan jose
joseph joshua julia justin karen kate kenneth kevin kim larry laura linda lisa mark martin mary matthew michael michelle mike nancy
nicholas patricia patrick paul peter rachel raymond rebecca richard robert roger ronald ryan sam samuel sandra sarah scott sean
stephen steve steven susan taylor thomas tim timothy tom tony victoria walter william yaroslav masayuki thanawut dazhon aaron
kanye keith murat eliot taylor ron rishi narendra joe kamala volodymyr vladimir xi recep keir emmanuel giorgia javier justin
""".split())


GENERIC_AIID = re.compile(
    r"scam|actor|criminal|creator|spreader|hacker|launderer|stalker|perpetrator|fraudster|propagand|\b(unnamed|unknown|"
    r"students?|minors?|boys|girls|men|women|teen\w*|children|parents|lawyers?|law firms?|attorneys?|employees|workers|users?|cells?|gangs?|gtg|reddit user\w*|"
    r"tools|developers|deployers|operators|providers|individuals?|people|public|researchers|journalists|influencers|"
    r"accounts?|campaigns?|networks?|groups? of|extortion\w*|blackmail\w*|influence|fraud rings?|professionals|stakeholders|"
    r"anonymous|litigants|channels|telegram|state media|teachers|organizations|organisations|hospitals|teams|firms)\b", re.I)
ENTITY_FREQ: dict = {}  # slug -> number of AIID incidents naming it (filled by load)


def pretty(slug: str) -> str:
    name = slug.replace("-", " ").strip()
    return " ".join(w if w.isupper() or "." in w or w.startswith("(") else w.capitalize() for w in name.split())


def is_person(name: str) -> bool:
    words = name.split()
    return 2 <= len(words) <= 3 and words[0].lower() in FIRST_NAMES and not co.ORG_SUFFIX_RX.search(name)


def _two_or_three_words(name):
    words = name.split()
    return 2 <= len(words) <= 3 and all(w[:1].isalpha() and w[:1].isupper() for w in words)


def classify_entity(slug: str):
    """Return (display_name, kind) for one AIID entity slug."""
    name = pretty(slug)
    known = co.find_companies(name)
    generic = co.GENERIC_RX.match(name) or GENERIC_AIID.search(name)
    if known and not generic:  # "Reddit Users" is a group of people, not Reddit
        return known[0], "Company"
    if is_person(name) or (_two_or_three_words(name) and ENTITY_FREQ.get(slug, 0) <= 2 and not co.ORG_SUFFIX_RX.search(name)
                           and not co.GOVERNMENT_RX.search(name) and not GENERIC_AIID.search(name)):
        return "", "Individual"  # rarely-named "Firstname Lastname" entities are most likely people
    if generic:
        return "", "Unidentified / malicious actors"
    if co.GOVERNMENT_RX.search(name):
        return name, "Government / public body"
    return name, "Company"


def responsible(deployers, developers):
    """Pick the responsible party: first named company among deployers, then developers."""
    ents = [classify_entity(s) for s in deployers] + [classify_entity(s) for s in developers]
    for kinds in (("Company",), ("Government / public body",), ("Individual", "Unidentified / malicious actors")):
        for name, kind in ents:
            if kind in kinds:
                return name, kind
    return "", "Not identified"


def display(slugs):
    out = []
    for s in slugs:
        name, kind = classify_entity(s)
        label = name or ("Individual" if kind == "Individual" else pretty(s))
        if label not in out:
            out.append(label)
    return "; ".join(out)


def load(raw=RAW) -> pd.DataFrame:
    raw = Path(raw)
    inc = pd.read_csv(raw / "incidents.csv")
    dups = pd.read_csv(raw / "duplicates.csv")["duplicate_incident_number"].tolist() if (raw / "duplicates.csv").exists() else []
    inc = inc[~inc["incident_id"].isin(dups)].copy()

    def parse(v):
        try:
            return json.loads(v) if isinstance(v, str) else []
        except json.JSONDecodeError:
            return []

    inc["deployers"] = inc["Alleged deployer of AI system"].map(parse)
    inc["developers"] = inc["Alleged developer of AI system"].map(parse)
    inc["harmed"] = inc["Alleged harmed or nearly harmed parties"].map(parse)
    inc["report_ids"] = inc["reports"].map(parse)
    inc["report_count"] = inc["report_ids"].map(len)
    ENTITY_FREQ.clear()
    for lst in list(inc["deployers"]) + list(inc["developers"]) + list(inc["harmed"]):
        for slug in set(lst):
            ENTITY_FREQ[slug] = ENTITY_FREQ.get(slug, 0) + 1

    resp = inc.apply(lambda r: responsible(r["deployers"], r["developers"]), axis=1)
    inc["responsible_company"] = [r[0] for r in resp]
    inc["entity_type"] = [r[1] for r in resp]
    inc["alleged_deployer"] = inc["deployers"].map(display)
    inc["alleged_developer"] = inc["developers"].map(display)
    inc["harmed_parties"] = inc["harmed"].map(
        lambda s: "; ".join(dict.fromkeys(pretty(x) for x in s if not is_person(pretty(x)) and "'s" not in x)))

    if (raw / "classifications_MIT.csv").exists():
        mit = pd.read_csv(raw / "classifications_MIT.csv").rename(columns={
            "Incident ID": "incident_id", "Risk Domain": "mit_risk_domain", "Risk Subdomain": "mit_risk_subdomain",
            "Entity": "mit_entity", "Timing": "mit_timing", "Intent": "mit_intent"})
        inc = inc.merge(mit[["incident_id", "mit_risk_domain", "mit_risk_subdomain", "mit_entity", "mit_timing", "mit_intent"]]
                        .drop_duplicates("incident_id"), on="incident_id", how="left")

    if (raw / "report_titles.csv").exists():
        rt = pd.read_csv(raw / "report_titles.csv").set_index("report_number")["title"].dropna()
        inc["report_titles"] = inc["report_ids"].map(lambda ids: " | ".join(rt.get(i, "") for i in ids[:5] if i in rt.index))
    else:
        inc["report_titles"] = ""

    inc["url"] = inc["incident_id"].map(lambda n: f"https://incidentdatabase.ai/cite/{n}/")
    return inc.drop(columns=["_id", "reports", "report_ids", "deployers", "developers", "harmed",
                             "Alleged deployer of AI system", "Alleged developer of AI system",
                             "Alleged harmed or nearly harmed parties"])
