"""
Build data/policies.csv and data/jurisdictions.csv for the AI Policy & Regulation Explorer.

Merges two open datasets:
  * AI Policy Tracker (aipolicytracker.org) — data CC BY 4.0, ~120 jurisdictions worldwide
  * Global AI Atlas (GAIA)               — MIT, deep US federal + state coverage, national laws

Usage:
    git clone --depth 1 https://github.com/8h45k4r/aipolicytracker.git
    git clone --depth 1 https://github.com/artvana/global-ai-atlas.git
    python build_policies.py aipolicytracker global-ai-atlas
"""
import difflib
import glob
import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

from iso_codes import ISO2_TO_ISO3, US_STATES

# ---------------------------------------------------------------------------
# Normalisation tables
# ---------------------------------------------------------------------------
INSTRUMENT = {
    "act": "Law / act", "statute": "Law / act", "ordinance": "Law / act",
    "bill": "Bill / draft law", "draft_law": "Bill / draft law", "consultation": "Bill / draft law",
    "regulation": "Regulation / rule", "administrative_rule": "Regulation / rule", "directive": "Regulation / rule",
    "executive_order": "Executive order",
    "strategy": "National strategy / plan", "policy": "National strategy / plan", "policy_framework": "National strategy / plan",
    "resolution": "National strategy / plan",
    "guidance": "Guidance / framework", "guidelines": "Guidance / framework", "framework": "Guidance / framework",
    "voluntary_framework": "Guidance / framework",
    "standard": "Standard / code of practice", "code_of_practice": "Standard / code of practice",
    "treaty": "International agreement", "international_agreement": "International agreement",
}
BINDING_TYPES = {"Law / act", "Regulation / rule", "Executive order"}

STATUS = {
    "in_force": "In force / adopted", "adopted": "In force / adopted", "guidance": "In force / adopted",
    "voluntary_standard": "In force / adopted", "partially_applicable": "In force / adopted",
    "enacted_not_yet_effective": "Enacted, not yet effective",
    "proposed": "Proposed / in consultation", "under_consultation": "Proposed / in consultation",
    "failed": "Failed / vetoed / withdrawn", "vetoed": "Failed / vetoed / withdrawn", "withdrawn": "Failed / vetoed / withdrawn",
    "superseded": "Superseded / repealed", "repealed": "Superseded / repealed", "rescinded": "Superseded / repealed",
    "archived": "Superseded / repealed",
}

TOPIC_RULES = {
    "General AI governance": r"general_ai_governance|ai governance|algorithmic_systems|cross_sector|ai_ethics|systemic_risk|high_risk|prohibited",
    "Deepfakes & synthetic media": r"synthetic|deepfake|content_labelling|voice_likeness|transparency_risk",
    "Employment & HR": r"employment|labor",
    "Health": r"health",
    "Education": r"education",
    "Government use of AI": r"government|public_services|public_authority",
    "Consumer protection": r"consumer",
    "Law enforcement & justice": r"criminal_justice|law_enforcement|migration_border",
    "Data protection & privacy": r"data_protection|biometric|privacy",
    "Elections": r"election",
    "Financial services": r"financial",
    "National security & defence": r"national_security|cybersecurity|critical_infrastructure",
    "Online safety & children": r"content_moderation|child_safety|media_information",
    "Copyright & IP": r"intellectual_property|copyright",
    "Frontier / general-purpose AI": r"gpai|frontier|generative_ai|foundation",
}

# Dates for well-known instruments whose source record has none (official adoption/publication dates).
KNOWN_DATES = {
    "us-nist-ai-rmf": "2023-01-26",
    "us-eo-14179": "2025-01-23",
    "us-omb-m-25-21": "2025-04-03",
    "us-americas-ai-action-plan": "2025-07-23",
    "uk-ai-opportunities-action-plan": "2025-01-13",
    "uk-ai-regulation-framework": "2023-03-29",
    "canada-voluntary-code-of-conduct-generative-ai": "2023-09-27",
    "council-of-europe-framework-convention-on-ai": "2024-05-17",
    "council-of-europe-huderia": "2024-11-28",
    "peru-ley-31814": "2023-07-05",
    "india-indiaai-mission": "2024-03-07",
    "japan-ai-guidelines-for-business": "2024-04-19",
}
KNOWN_TITLE_DATES = [  # (jurisdiction, short-title regex, date)
    ("us", r"NIST AI RMF", "2023-01-26"),
    ("us", r"EO 14179", "2025-01-23"),
    ("us", r"OMB M-25-21", "2025-04-03"),
    ("us", r"America's AI Action Plan", "2025-07-23"),
    ("uk", r"AI Opportunities Action Plan", "2025-01-13"),
    ("uk", r"UK AI regulation framework", "2023-03-29"),
    ("canada", r"Voluntary Code of Conduct", "2023-09-27"),
    ("canada", r"Pan-Canadian", "2017-03-22"),
    ("council-of-europe", r"Framework Convention", "2024-05-17"),
    ("council-of-europe", r"HUDERIA", "2024-11-28"),
    ("peru", r"31814", "2023-07-05"),
    ("india", r"IndiaAI Mission", "2024-03-07"),
    ("india", r"National Strategy for Artificial Intelligence", "2018-06-04"),
    ("japan", r"AI Guidelines for Business", "2024-04-19"),
]

ATLAS_NAME_FIX = {"UAE": "United Arab Emirates", "EU": "European Union", "Korea": "South Korea", "Turkey": "Türkiye",
                  "Hong Kong SAR": "Hong Kong SAR", "Brunei Darussalam": "Brunei",
                  "NIST": "United States", "FTC": "United States", "Federal Trade Commission": "United States", "DHS": "United States",
                  "CFPB": "United States", "EEOC": "United States", "SEC": "United States", "FDA": "United States",
                  "SG": "Singapore", "Ivory Coast": "Côte d'Ivoire", "AU": "African Union",
                  "ASEAN": "ASEAN (Association of Southeast Asian Nations)", "National Assembly": "South Korea"}
INTERNATIONAL_BODIES = r"^(G7|G20|OECD|UNESCO|UNICEF|United Nations|UN|World Health Organization|WHO|Financial Stability Board|Organization of American States|ISO/IEC|International|Global Partnership.*|Bletchley.*|Basel Committee.*|IOSCO|APEC|BRICS|NATO|G7 / OECD|Gulf Cooperation Council)$"
MAX_YEAR = 2026  # ignore target years in titles such as "Vision 2030"


def topics_for(*values):
    text = " ".join(str(v) for v in values if v).lower()
    found = [t for t, rx in TOPIC_RULES.items() if re.search(rx, text)]
    return "; ".join(found) if found else "General AI governance"


def first_date(*candidates):
    for c in candidates:
        if not c:
            continue
        m = re.search(r"(?:19|20)\d\d(?:-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?)?(?!\d)", str(c))
        if m and int(m.group(0)[:4]) <= MAX_YEAR:
            d = m.group(0)
            return d if len(d) == 10 else (d + "-01-01" if len(d) == 4 else d + "-01"), len(d)
    return None, 0


# ---------------------------------------------------------------------------
def load_jurisdictions(apt):
    rows = {}
    for f in glob.glob(f"{apt}/data/jurisdictions/*.yaml"):
        j = yaml.safe_load(open(f))
        iso2 = j.get("iso_code") or ""
        level = {"country": "National", "territory": "National", "state": "Subnational", "supranational": "Supranational"}.get(j.get("jurisdiction_type"), "International")
        country = j["name"]
        if iso2.startswith("US-"):
            country = "United States"
        if iso2.startswith("CA-"):
            country = "Canada"
        rows[j["slug"]] = {
            "slug": j["slug"], "jurisdiction": j["name"], "country": country, "level": level,
            "iso2": iso2[:2] if level != "Supranational" else "",
            "iso3": ISO2_TO_ISO3.get(iso2[:2], "") if level in ("National", "Subnational") else "",
            "region": j.get("region") or "International", "subregion": j.get("subregion") or "",
            "status_summary": re.sub(r"\s+", " ", (j.get("regulatory_status_summary") or "").strip()),
        }
    return rows


def from_apt(apt, J):
    out = []
    for f in glob.glob(f"{apt}/data/policies/*/*.yaml"):
        p = yaml.safe_load(open(f))
        if not p.get("published", True):
            continue
        j = J.get(p["jurisdiction"], {})
        versions = [v for v in p.get("versions") or [] if v.get("version_date")]
        adopted = [v for v in versions if not re.search(r"proposal|draft|consultation|introduced", v.get("version_label") or "", re.I)]
        dates = sorted(str(v["version_date"]) for v in (adopted or versions))
        date, prec = first_date(*dates)  # earliest adopted version = original adoption
        if not date:
            for jur, rx, d in KNOWN_TITLE_DATES:
                if p["jurisdiction"] == jur and re.search(rx, (p.get("short_title") or "") + " " + p["title"]):
                    date, prec = d, 10
                    break
        if not date:
            date, prec = first_date(p.get("short_title"), p["title"])
        itype = INSTRUMENT.get(p.get("instrument_type"), "Guidance / framework")
        out.append({
            "id": "APT-" + p["slug"],
            "jurisdiction": j.get("jurisdiction", p["jurisdiction"]),
            "country": j.get("country", ""),
            "state": re.sub(r"\s*\(.*\)$", "", j["jurisdiction"]) if j.get("level") == "Subnational" else "",
            "level": j.get("level", "National"),
            "iso3": j.get("iso3", ""),
            "region": j.get("region", ""),
            "title": p["title"].strip(),
            "short_title": (p.get("short_title") or p["title"]).strip(),
            "instrument_type": itype,
            "binding": bool(p.get("is_binding")),
            "status": STATUS.get(p.get("status"), "In force / adopted"),
            "date": date,
            "year": int(date[:4]) if date else None,
            "date_precision": {10: "day", 7: "month", 4: "year"}.get(prec, "unknown"),
            "topics": topics_for(p.get("sectors"), p.get("risk_categories"), p.get("actors"), p.get("instrument_type"), p.get("summary_plain")),
            "issuing_body": p.get("issuing_body") or "",
            "summary": re.sub(r"\s+", " ", (p.get("summary_plain") or "").strip()),
            "scope": re.sub(r"\s+", " ", (p.get("scope_summary") or "").strip()),
            "url": p.get("official_source_url") or "",
            "dataset": "AI Policy Tracker (CC BY 4.0)",
        })
    return out


def from_atlas(atlas, J):
    by_name = {v["jurisdiction"].lower(): v for v in J.values()}
    out = []
    for r in json.load(open(f"{atlas}/data/regulations.json")):
        raw = re.sub(r"\s*\(.*\)\s*$", "", r.get("jurisdiction") or "").strip()  # "Canada (ISED)" -> "Canada"
        jname = ATLAS_NAME_FIX.get(raw, raw)
        jt = r.get("jurisdiction_type")
        if re.match(INTERNATIONAL_BODIES, jname):
            level, country, state, region = "International", "", "", "International"
            jname = "International organisations (OECD, UNESCO, UN, G7, ISO)"
        elif jt == "subnational" or jname in US_STATES:
            level, country, state, region = "Subnational", "United States", jname, "Americas"
            jname = f"{jname} (United States)"
        elif jt == "supranational" or jname in ("European Union", "ASEAN (Association of Southeast Asian Nations)", "African Union", "Council of Europe"):
            level, country, state, region = "Supranational", "", "", by_name.get(jname.lower(), {}).get("region", "International")
        else:
            j = by_name.get(jname.lower(), {})
            level, country, state, region = "National", jname, "", j.get("region", "")
        iso3 = "USA" if country == "United States" else by_name.get(country.lower(), {}).get("iso3", "")
        date, prec = first_date(r.get("enacted_date"), r.get("effective_date"), r.get("last_action_date"), r.get("bill_number"), r.get("short_name"))
        itype = INSTRUMENT.get(r.get("instrument_type"), "Guidance / framework")
        status = STATUS.get(r.get("status"), "Proposed / in consultation")
        out.append({
            "id": "GAIA-" + r["id"],
            "jurisdiction": jname,
            "country": country,
            "state": state,
            "level": level,
            "iso3": iso3,
            "region": region,
            "title": (r.get("full_name") or r.get("short_name") or "").strip(),
            "short_title": (r.get("short_name") or r.get("full_name") or "").strip(),
            "instrument_type": itype,
            "binding": itype in BINDING_TYPES and status in ("In force / adopted", "Enacted, not yet effective"),
            "status": status,
            "date": date,
            "year": int(date[:4]) if date else None,
            "date_precision": {10: "day", 7: "month", 4: "year"}.get(prec, "unknown"),
            "topics": topics_for(r.get("categories"), r.get("primary_category"),
                                 [k for k, v in (r.get("provisions") or {}).items() if v is True]),
            "issuing_body": "; ".join(r.get("enforcement_body") or []) if isinstance(r.get("enforcement_body"), list) else (r.get("enforcement_body") or ""),
            "summary": re.sub(r"\s+", " ", (r.get("summary") or "").strip()),
            "scope": r.get("scope") or "",
            "url": r.get("official_text_url") or r.get("summary_url") or "",
            "dataset": "Global AI Atlas (MIT)",
        })
    return out


def _core(title, jurisdiction):
    t = re.sub(r"\(.*?\)", " ", title.lower()).replace("artificial intelligence", "ai")
    for w in re.findall(r"\w+", jurisdiction.lower()):
        t = re.sub(rf"\b{re.escape(w)}\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _numbers(title):
    return {n for n in re.findall(r"\b\d{3,5}\b", title) if not re.fullmatch(r"(19|20)\d\d", n)}


def is_duplicate(row, kept):
    for k in kept:
        if k["jurisdiction"].lower() != row["jurisdiction"].lower():
            continue
        if _numbers(row["title"] + " " + row["short_title"]) & _numbers(k["title"] + " " + k["short_title"]):
            return k
        ca, cb = _core(row["short_title"], row["jurisdiction"]), _core(k["short_title"], k["jurisdiction"])
        short, long_ = sorted([ca, cb], key=len)
        if len(short) >= 8 and (set(ca.split()) == set(cb.split()) or (short in long_ and len(short) >= 0.7 * len(long_))):
            return k

        a, b = row["short_title"].lower(), k["short_title"].lower()
        ta, tb = row["title"].lower(), k["title"].lower()
        if difflib.SequenceMatcher(None, a, b).ratio() > 0.75 or difflib.SequenceMatcher(None, ta, tb).ratio() > 0.8:
            return k
        if row["year"] and row["year"] == k["year"] and row["instrument_type"] == k["instrument_type"] and row["level"] != "Subnational":
            return k
    return None


def main(apt, atlas):
    J = load_jurisdictions(apt)
    primary = from_apt(apt, J)
    merged = list(primary)
    for r in from_atlas(atlas, J):
        dup = is_duplicate(r, primary)
        if dup is None:
            merged.append(r)
        elif not dup["date"] and r["date"]:  # borrow a precise date from the duplicate record
            dup.update(date=r["date"], year=r["year"], date_precision=r["date_precision"])
    df = pd.DataFrame(merged).sort_values(["date", "jurisdiction"], ascending=[False, True], na_position="last")
    out = Path(__file__).parent / "data"
    out.mkdir(exist_ok=True)
    df.to_csv(out / "policies.csv", index=False)

    jdf = pd.DataFrame(J.values())
    counts = df.groupby("jurisdiction").agg(
        instruments=("id", "size"),
        binding_in_force=("binding", lambda s: int((s & df.loc[s.index, "status"].isin(["In force / adopted", "Enacted, not yet effective"])).sum())),
    ).reset_index()
    jdf = jdf.merge(counts, on="jurisdiction", how="left").fillna({"instruments": 0, "binding_in_force": 0})
    jdf.to_csv(out / "jurisdictions.csv", index=False)
    print(f"Wrote {len(df):,} policy instruments ({len(primary)} from AI Policy Tracker) and {len(jdf)} jurisdictions")
    return df


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "aipolicytracker", sys.argv[2] if len(sys.argv) > 2 else "global-ai-atlas")
