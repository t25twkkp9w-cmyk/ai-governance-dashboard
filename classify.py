"""
Build data/incidents_classified.csv from the open GenAI & Agentic AI incident
corpus (CC BY 4.0), which aggregates the AI Incident Database (AIID), OECD AI
Incidents Monitor, AIAAIC and the MIT AI Risk Repository.

Usage:
    python classify.py path/to/incidents.json

Get the source file with:
    git clone --depth 1 https://github.com/emmanuelgjr/genai_agentic_incidents.git
    python classify.py genai_agentic_incidents/data/incidents.json
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

import aiid
import companies as co
import frameworks as fw

# OECD AIM also logs positive uses and hazards; these should not rank as top risks.
BENEFIT_RX = re.compile(
    r"\b(prevents?|prevented|halves|saves? (lives|\d)|successfully|improves? .{0,40}(detection|outcomes|safety|diagnos)|"
    r"reduces? (traffic )?(accidents|deaths|crime|errors|vascular events|fatalities)|recovers? stolen|recovery of stolen|"
    r"aids? (arrest|fight|rescue|recovery)|rescue|early .{0,25}detection|detects? .{0,30}early)\b", re.I)
HARM_WORDS = re.compile(r"\b(fail|harm|risk|concern|death|kill|injur|leak|breach|bias|discriminat|lawsuit|sued|scam|fraud|"
                        r"deepfake|misuse|error|wrong|hack|vulnerab|weapon|military|drone|combat|strike|evade|bypass|target)", re.I)

BOILERPLATE = re.compile(r"^Tracked by the OECD AI Incidents and Hazards Monitor", re.I)


def rx(pattern):
    """Every alternative must start on a word boundary ('rce' must not match 'force')."""
    return re.compile(r"\b(?:" + pattern + ")", re.I)


def compile_rules(rules):
    return [(label, rx(p)) for label, p in rules]


UNACC = compile_rules(fw.EU_UNACCEPTABLE)
HIGH = compile_rules(fw.EU_HIGH_RISK)
LIMITED = compile_rules(fw.EU_LIMITED)
GPAI = rx(fw.EU_GPAI)
MILITARY = rx(fw.EU_MILITARY)
NIST_CHAR = {k: rx(v) for k, v in fw.NIST_CHARACTERISTICS.items()}
HARMS = {k: rx(v) for k, v in fw.HARM_TYPES.items()}

SOURCE_EU_TAGS = {
    "eu-ai-act-1-unacceptable": "Unacceptable (Art. 5)",
    "eu-ai-act-2-high-risk": "High-risk (Annex I/III)",
    "eu-ai-act-3-limited-risk": "Limited / transparency (Art. 50)",
    "eu-ai-act-4-minimal-or-no-risk": "Minimal",
}


def first_match(rules, text):
    for label, rx in rules:
        if rx.search(text):
            return label
    return None


def incident_text(i):
    desc = i.get("description") or ""
    if BOILERPLATE.match(desc):
        desc = ""  # OECD stubs carry no narrative, only the title is useful
    return " ".join([i.get("title") or "", desc, i.get("affected") or "", i.get("_report_titles") or ""])


def classify_harm(text, vector):
    for harm, rx in HARMS.items():
        if rx.search(text):
            return harm
    return fw.VECTOR_TO_HARM.get(vector, "Other")


def classify_eu(text, harm, tags):
    """Return (tier, basis, method)."""
    basis = first_match(UNACC, text)
    if basis:
        return "Unacceptable (Art. 5)", basis, "rule"
    if MILITARY.search(text):
        return "Out of scope (military, Art. 2(3))", "Art. 2(3) military/defence exclusion", "rule"
    # A deepfake of a student is a transparency issue, not an education system.
    if harm == "Deepfakes & Misinformation":
        basis = first_match(LIMITED, text)
        if basis:
            return "Limited / transparency (Art. 50)", basis, "rule"
    basis = first_match(HIGH, text)
    # Students cheating *with* AI is misuse, not an AI system making education decisions.
    if basis == "Annex III(3) education" and re.search(r"cheat", text, re.I):
        basis = None
    if basis:
        return "High-risk (Annex I/III)", basis, "rule"
    m = GPAI.search(text)
    if m:
        return "GPAI obligations (Ch. V)", f"Ch. V general-purpose AI ({m.group(0)})", "rule"
    basis = first_match(LIMITED, text)
    if basis:
        return "Limited / transparency (Art. 50)", basis, "rule"
    for t in tags:  # fall back to the curated label from the MIT AI Risk Repository
        if t in SOURCE_EU_TAGS:
            return SOURCE_EU_TAGS[t], "Source label (MIT AI Risk Repository)", "source"
    return "Minimal", "No high-risk domain or transparency trigger detected", "rule"


def nist_characteristics(text, harm):
    chars = [k for k, rx in NIST_CHAR.items() if rx.search(text)]
    default = {
        "Privacy & Data Protection": "Privacy-Enhanced",
        "Bias & Discrimination": "Fair – Harmful Bias Managed",
        "Deepfakes & Misinformation": "Accountable & Transparent",
        "Security & Malicious Use": "Secure & Resilient",
        "Safety & Physical Harm": "Safe",
        "Reliability & Hallucination": "Valid & Reliable",
        "Surveillance & Rights": "Privacy-Enhanced",
        "Military & Geopolitical": "Safe",
        "Governance & Accountability": "Accountable & Transparent",
        "Toxic & Harmful Content": "Safe",
        "Economic, IP & Societal Impact": "Accountable & Transparent",
    }.get(harm)
    if default and default not in chars:
        chars.insert(0, default)
    elif default:
        chars.remove(default)
        chars.insert(0, default)
    return chars or ["Valid & Reliable"]


def nist_function(subcats, harm):
    funcs = Counter(s.split("-")[0] for s in subcats if s.split("-")[0] in fw.NIST_FUNCTIONS)
    if funcs:
        return funcs.most_common(1)[0][0]
    return {
        "Governance & Accountability": "GOVERN",
        "Economic, IP & Societal Impact": "GOVERN",
        "Military & Geopolitical": "GOVERN",
        "Surveillance & Rights": "MAP",
        "Bias & Discrimination": "MEASURE",
        "Reliability & Hallucination": "MEASURE",
    }.get(harm, "MANAGE")


def normalize_date(d):
    d = (d or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        return d, "day"
    if re.fullmatch(r"\d{4}-\d{2}", d):
        return d + "-01", "month"
    if re.fullmatch(r"\d{4}", d):
        return d + "-01-01", "year"
    return None, "unknown"


def source_of(i):
    tags = set(i.get("tags", []))
    if i.get("aiid_id") or "aiid" in tags:
        return "AIID"
    if "oecd-aim" in tags:
        return "OECD AIM"
    if "aiaaic" in tags:
        return "AIAAIC"
    if "airi-navigator" in tags:
        return "MIT AI Risk Repository"
    return "Other / research"


def tag_value(tags, prefix):
    vals = [t[len(prefix):] for t in tags if t.startswith(prefix)]
    return vals[0].replace("-", " ").title() if vals else "Unknown"


MIT_DOMAINS = {
    "1": "1. Discrimination and Toxicity", "2": "2. Privacy & Security", "3": "3. Misinformation",
    "4": "4. Malicious Actors & Misuse", "5": "5. Human-Computer Interaction",
    "6": "6. Socioeconomic & Environmental Harms", "7": "7. AI system safety, failures, and limitations",
}
SEV_CRITICAL = re.compile(r"\b(died|death|deaths|killed|kills?|fatal\w*|suicide|manslaughter|shooting)\b", re.I)
SEV_HIGH = re.compile(r"\b(injur\w*|hospitali[sz]\w*|arrest\w*|wrongful\w*|jail\w*|leak\w*|breach\w*|lawsuit|sued|"
                      r"fraud|scam\w*|stole|theft|extort\w*|child sexual|csam|nude|discriminat\w*|denied|evict\w*)\b", re.I)


def aiid_severity(text):
    return "Critical" if SEV_CRITICAL.search(text) else "High" if SEV_HIGH.search(text) else "Medium"


def merge_aiid(data, aiid_df):
    """Enrich corpus records with the AIID snapshot and add AIID incidents the corpus doesn't have yet."""
    by_id = {int(r.incident_id): r for r in aiid_df.itertuples()}
    seen = set()
    for i in data:
        n = i.get("aiid_id")
        if n and int(n) in by_id:
            r = by_id[int(n)]
            seen.add(int(n))
            i.update(title=r.title, description=r.description, _aiid=r, _report_titles=r.report_titles,
                     date=r.date if isinstance(r.date, str) else i.get("date"))
    new = []
    for n, r in by_id.items():
        if n in seen:
            continue
        text = f"{r.title} {r.description} {r.report_titles}"
        new.append({
            "id": f"AIID-{n}", "aiid_id": n, "title": r.title, "date": r.date, "year": int(str(r.date)[:4]),
            "category": "real-world", "description": r.description, "attack_vector": "other",
            "severity": aiid_severity(text), "tags": ["aiid"], "nist_ai_rmf": [], "references": [{"url": r.url}],
            "_aiid": r, "_report_titles": r.report_titles,
        })
    print(f"AIID snapshot: enriched {len(seen):,} incidents, added {len(new):,} new ones")
    return data + new



def drop_cross_source_duplicates(df, matches_path):
    """Merge incidents that AIID and another database (AIAAIC / OECD) both recorded.

    Pairs come from data/raw/aiid/cross_source_matches.csv: candidates found by date window and
    title/description similarity, each confirmed by manual review. The AIID record is kept (it has the
    full description and entity fields); the duplicate is dropped and credited in `also_reported_by`.
    """
    df["also_reported_by"] = ""
    if not Path(matches_path).exists():
        return df
    m = pd.read_csv(matches_path)
    keep = df[df["aiid_id"].astype(str) != ""].copy()
    keep_idx = {int(float(a)): i for i, a in zip(keep.index, keep["aiid_id"])}
    by_id = df.set_index("id")
    drop = []
    for r in m.itertuples():
        if r.duplicate_id not in by_id.index or r.aiid_incident not in keep_idx:
            continue
        dup = by_id.loc[r.duplicate_id]
        i = keep_idx[r.aiid_incident]
        label = f"{dup['source']} ({dup['url']})" if dup["url"] else dup["source"]
        df.at[i, "also_reported_by"] = "; ".join(x for x in [df.at[i, "also_reported_by"], label] if x)
        for col in ["sector", "jurisdiction"]:  # AIAAIC tags these; AIID records often lack them
            if df.at[i, col] == "Unknown" and dup[col] != "Unknown":
                df.at[i, col] = dup[col]
        drop.append(r.duplicate_id)
    print(f"Merged {len(drop)} cross-source duplicates into their AIID records")
    return df[~df["id"].isin(drop)]


def drop_aiaaic_oecd_duplicates(df, matches_path):
    """Merge OECD entries that duplicate an AIAAIC incident (pairs confirmed by manual review).

    The AIAAIC record is kept: it has the system, sector and jurisdiction fields, while OECD entries carry only a title.
    """
    if not Path(matches_path).exists():
        return df
    m = pd.read_csv(matches_path)
    idx = {i: n for n, i in zip(df.index, df["id"])}
    drop = []
    for r in m.itertuples():
        if r.keep_id not in idx or r.duplicate_id not in idx:
            continue
        k, dup = idx[r.keep_id], df.loc[idx[r.duplicate_id]]
        label = f"{dup['source']} ({dup['url']})" if dup["url"] else dup["source"]
        df.at[k, "also_reported_by"] = "; ".join(x for x in [df.at[k, "also_reported_by"], label] if x)
        if df.at[k, "date_precision"] == "year" and dup["date_precision"] == "day":  # OECD has the exact date
            df.at[k, "date"], df.at[k, "date_precision"] = dup["date"], "day"
        drop.append(r.duplicate_id)
    print(f"Merged {len(drop)} OECD duplicates into their AIAAIC records")
    return df[~df["id"].isin(drop)]


def main(src, aiid_dir=None):
    data = json.loads(Path(src).read_text())["incidents"]
    aiid_dir = Path(aiid_dir) if aiid_dir else aiid.RAW
    if (aiid_dir / "incidents.csv").exists():
        data = merge_aiid(data, aiid.load(aiid_dir))
    rows = []
    for i in data:
        if i.get("category") == "vulnerability-disclosure" or i.get("status") == "retracted":
            continue  # keep real-world harms; skip CVE software bugs
        text = incident_text(i)
        tags = i.get("tags", [])
        harm = classify_harm(text, i.get("attack_vector"))
        tier, basis, method = classify_eu(text, harm, tags)
        chars = nist_characteristics(text, harm)
        subcats = i.get("nist_ai_rmf", [])
        iso = fw.HARM_TO_ISO[harm][:]
        if re.search(r"vendor|supplier|third[- ]party|supply[- ]chain|plugin|integration", text, re.I):
            iso.append("A.10.3")
        if tier == "High-risk (Annex I/III)" and "A.5.2" not in iso:
            iso.append("A.5.2")
        date, precision = normalize_date(i.get("date"))
        sev = i.get("severity", "Medium")
        refs = i.get("references") or []
        a = i.get("_aiid")
        if a is not None:
            company, entity_type, company_method = a.responsible_company, a.entity_type, "AIID deployer/developer"
            entities = "; ".join(x for x in [a.alleged_deployer, a.alleged_developer] if x)
        else:
            company, entities, entity_type, company_method = co.responsible_party(i.get("affected"), i.get("title"))
        mit_tag = next((t.split(":", 1)[1] for t in tags if t.startswith("mit-risk-domain:")), "")
        rows.append({
            "id": i["id"],
            "aiid_id": i.get("aiid_id") or "",
            "title": i.get("title", "").strip(),
            "date": date,
            "date_precision": precision,
            "year": int(date[:4]) if date else i.get("year"),
            "source": source_of(i),
            "responsible_company": company,
            "responsible_entities": entities,
            "entity_type": entity_type,
            "company_method": company_method,
            "alleged_deployer": a.alleged_deployer if a is not None else "",
            "alleged_developer": a.alleged_developer if a is not None else "",
            "harmed_parties": a.harmed_parties if a is not None else "",
            "mit_risk_domain": (a.mit_risk_domain if a is not None and isinstance(a.mit_risk_domain, str)
                                else MIT_DOMAINS.get(mit_tag[:1], "") if mit_tag else ""),
            "mit_intent": a.mit_intent if a is not None and isinstance(a.mit_intent, str) else "",
            "report_count": int(a.report_count) if a is not None else len(i.get("references") or []),
            "sector": tag_value(tags, "sector-"),
            "jurisdiction": tag_value(tags, "juris-").upper() if tag_value(tags, "juris-") in ("Usa", "Uk", "Eu") else tag_value(tags, "juris-"),
            "severity": sev,
            "harm_type": harm,
            "eu_ai_act_tier": tier,
            "eu_ai_act_basis": basis,
            "eu_tier_method": method,
            "nist_characteristic": chars[0],
            "nist_characteristics_all": "; ".join(chars),
            "nist_function": nist_function(subcats, harm),
            "nist_subcategories": "; ".join(subcats),
            "iso42001_primary": iso[0],
            "iso42001_primary_name": fw.ISO_CONTROLS[iso[0]],
            "iso42001_group": fw.ISO_GROUPS[".".join(iso[0].split(".")[:2])],
            "iso42001_controls": "; ".join(dict.fromkeys(iso)),
            "story_type": "Positive use / benefit" if BENEFIT_RX.search(i.get("title") or "") and not HARM_WORDS.search(i.get("title") or "") else "Harm or hazard",
            # No identified harm (often hazard/news items): cap severity at Medium
            "risk_score": (min(fw.SEVERITY_WEIGHT.get(sev, 2), 2) if harm == "Other" else fw.SEVERITY_WEIGHT.get(sev, 2)) * fw.EU_TIER_WEIGHT[tier] * 5,
            "attack_vector": i.get("attack_vector", ""),
            "description": "" if BOILERPLATE.match(i.get("description") or "") else (i.get("description") or "").strip(),
            "url": refs[0]["url"] if refs else "",
        })
    df = pd.DataFrame(rows).sort_values("date", ascending=False)
    df = drop_cross_source_duplicates(df, aiid_dir / "cross_source_matches.csv")
    df = drop_aiaaic_oecd_duplicates(df, Path(__file__).parent / "data" / "raw" / "aiaaic_oecd_matches.csv")
    df.loc[df["story_type"] == "Positive use / benefit", "risk_score"] = 5  # benefits are logged, not ranked as risks
    out = Path(__file__).parent / "data" / "incidents_classified.csv"
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df):,} incidents to {out}")
    print(df["eu_ai_act_tier"].value_counts().to_string())
    return df


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "genai_agentic_incidents/data/incidents.json",
         sys.argv[2] if len(sys.argv) > 2 else None)
