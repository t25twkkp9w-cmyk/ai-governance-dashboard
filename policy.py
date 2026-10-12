"""
AI Policy & Regulation Explorer: data access, search ("ask the policies"),
country comparison and the link between incidents and regulation.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path

import pandas as pd

import llm

DATA = Path(__file__).parent / "data"
IN_EFFECT = ["In force / adopted", "Enacted, not yet effective"]
TOPICS = [
    "General AI governance", "Frontier / general-purpose AI", "Deepfakes & synthetic media", "Employment & HR",
    "Health", "Education", "Government use of AI", "Consumer protection", "Law enforcement & justice",
    "Data protection & privacy", "Elections", "Financial services", "National security & defence",
    "Online safety & children", "Copyright & IP",
]

# Country name -> regex of how incidents refer to it (name, demonym, common abbreviations)
COUNTRY_PATTERNS = {
    "United States": r"\b(usa|u\.s\.|us|united states|american|america)\b|\b(california|texas|new york|florida|illinois|washington, d\.c\.)\b",
    "United Kingdom": r"\b(uk|u\.k\.|united kingdom|britain|british|england|english|scotland|scottish|wales|welsh|london)\b",
    "China": r"\b(china|chinese|beijing|shanghai|shenzhen)\b",
    "India": r"\b(india|indian|delhi|mumbai|bengaluru|bangalore)\b",
    "Japan": r"\b(japan|japanese|tokyo)\b",
    "South Korea": r"\b(south korea|south korean|korea|korean|seoul)\b",
    "Germany": r"\b(germany|german|berlin)\b",
    "France": r"\b(france|french|paris)\b",
    "Italy": r"\b(italy|italian|rome)\b",
    "Spain": r"\b(spain|spanish|madrid)\b",
    "Netherlands": r"\b(netherlands|dutch|amsterdam)\b",
    "Canada": r"\b(canada|canadian|ontario|quebec|toronto)\b",
    "Australia": r"\b(australia|australian|sydney|melbourne)\b",
    "Brazil": r"\b(brazil|brazilian|são paulo|sao paulo)\b",
    "Russia": r"\b(russia|russian|moscow|kremlin)\b",
    "Ukraine": r"\b(ukraine|ukrainian|kyiv)\b",
    "Israel": r"\b(israel|israeli)\b",
    "Türkiye": r"\b(turkey|turkish|türkiye|istanbul|ankara)\b",
    "Taiwan": r"\b(taiwan|taiwanese|taipei|kaohsiung)\b",
    "Singapore": r"\b(singapore)\b",
    "Indonesia": r"\b(indonesia|indonesian|jakarta|bali)\b",
    "Vietnam": r"\b(vietnam|vietnamese|hanoi)\b",
    "Thailand": r"\b(thailand|thai|bangkok)\b",
    "Philippines": r"\b(philippines|filipino|manila)\b",
    "Malaysia": r"\b(malaysia|malaysian)\b",
    "Pakistan": r"\b(pakistan|pakistani)\b",
    "Nigeria": r"\b(nigeria|nigerian)\b",
    "Kenya": r"\b(kenya|kenyan|nairobi)\b",
    "South Africa": r"\b(south africa|south african)\b",
    "Mexico": r"\b(mexico|mexican)\b",
    "Argentina": r"\b(argentina|argentine)\b",
    "Colombia": r"\b(colombia|colombian)\b",
    "Chile": r"\b(chile|chilean)\b",
    "Ireland": r"\b(ireland|irish|dublin)\b",
    "Poland": r"\b(poland|polish)\b",
    "Sweden": r"\b(sweden|swedish)\b",
    "Denmark": r"\b(denmark|danish)\b",
    "Norway": r"\b(norway|norwegian)\b",
    "Belgium": r"\b(belgium|belgian|brussels)\b",
    "Switzerland": r"\b(switzerland|swiss)\b",
    "New Zealand": r"\b(new zealand)\b",
    "United Arab Emirates": r"\b(uae|united arab emirates|emirati|dubai|abu dhabi)\b",
    "Saudi Arabia": r"\b(saudi)\b",
    "Iran": r"\b(iran|iranian|tehran)\b",
    "Hong Kong SAR": r"\b(hong kong)\b",
    "Egypt": r"\b(egypt|egyptian)\b",
}
_COUNTRY_RX = {c: re.compile(p, re.I) for c, p in COUNTRY_PATTERNS.items()}


def load_policies(path=DATA / "policies.csv") -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["binding"] = df["binding"].astype(bool)
    for c in ["summary", "scope", "issuing_body", "url", "state", "country", "iso3", "region", "topics"]:
        df[c] = df[c].fillna("")
    df["in_effect"] = df["status"].isin(IN_EFFECT)
    return df


def load_jurisdictions(path=DATA / "jurisdictions.csv") -> pd.DataFrame:
    return pd.read_csv(path).fillna({"status_summary": "", "iso3": "", "subregion": ""})


def has_topic(df, topic):
    return df["topics"].str.contains(re.escape(topic), na=False)


def incident_countries(incidents: pd.DataFrame) -> pd.Series:
    """Explode incidents to the countries they mention (jurisdiction tag + title)."""
    text = incidents["jurisdiction"].fillna("").str.replace("Unknown", "") + " " + incidents["title"].fillna("")
    out = {}
    for idx, t in text.items():
        hits = [c for c, rx in _COUNTRY_RX.items() if rx.search(t)]
        if hits:
            out[idx] = hits
    return pd.Series(out, dtype=object).explode()


def country_scorecard(policies, incidents):
    """One row per country: instruments, binding laws in effect, incidents mentioning it."""
    nat = policies[policies["level"].isin(["National", "Subnational"]) & (policies["country"] != "")]
    g = nat.groupby("country").agg(
        iso3=("iso3", "first"), region=("region", "first"), instruments=("id", "size"),
        binding_in_effect=("binding", lambda s: int((s & nat.loc[s.index, "in_effect"]).sum())),
        proposed=("status", lambda s: int((s == "Proposed / in consultation").sum())),
    )
    inc = incident_countries(incidents).value_counts().rename("incidents")
    g = g.join(inc, how="outer").fillna({"instruments": 0, "binding_in_effect": 0, "proposed": 0, "incidents": 0})
    g["iso3"] = g["iso3"].fillna("")
    return g.reset_index().rename(columns={"index": "country"})


# ---------------------------------------------------------------------------
# "Ask the policies": BM25 retrieval over titles + summaries, optional LLM answer
# ---------------------------------------------------------------------------
STOP = set("the a an of and or to in on for with by is are was be what which how does do did any about from as at it its this that "
           "there their have has who whom when where why can should would could laws law ai artificial intelligence policy policies".split())


def _tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", str(text).lower()) if t not in STOP and len(t) > 1]


class PolicyIndex:
    def __init__(self, df: pd.DataFrame, k1=1.4, b=0.75):
        self.df = df.reset_index(drop=True)
        docs = (self.df["jurisdiction"] + " " + self.df["short_title"] + " " + self.df["title"] + " "
                + self.df["topics"] + " " + self.df["instrument_type"] + " " + self.df["summary"]).map(_tokens)
        self.docs = [Counter(d) for d in docs]
        self.lens = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lens) / max(len(self.lens), 1)
        df_count = Counter(t for d in self.docs for t in d)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df_count.items()}
        self.k1, self.b = k1, b

    def search(self, query, k=8, jurisdictions=None):
        q = _tokens(query)
        scores = []
        for i, (d, L) in enumerate(zip(self.docs, self.lens)):
            s = 0.0
            for t in q:
                if t in d:
                    f = d[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * L / self.avg))
            if s > 0:
                scores.append((s, i))
        hits = self.df.iloc[[i for _, i in sorted(scores, reverse=True)]]
        if jurisdictions:
            hits = hits[hits["jurisdiction"].isin(jurisdictions) | hits["country"].isin(jurisdictions)]
        hits = hits.copy()
        # binding laws in effect first among near-equal matches
        return hits.head(k * 3).sort_values(["in_effect", "binding"], ascending=False, kind="stable").head(k)


def answer(question, hits: pd.DataFrame):
    """Grounded answer with numbered citations. Returns None when no LLM key is set."""
    if hits.empty:
        return "No matching instruments found. Try different words, or remove the jurisdiction filter."
    context = "\n\n".join(
        f"[{n}] {r.jurisdiction} — {r.short_title} ({r.instrument_type}; {r.status}; "
        f"{r.date.date() if pd.notna(r.date) else 'date n/a'}; binding={'yes' if r.binding else 'no'})\n{r.summary[:700]}"
        for n, r in enumerate(hits.itertuples(), 1)
    )
    return llm.chat(
        "You are an AI policy analyst. Answer the question using ONLY the numbered sources. Cite sources inline like [1]. "
        "Say clearly whether each instrument is binding and in force, proposed, or failed. If the sources don't answer "
        "the question, say so. Keep it under 200 words. This is not legal advice.",
        f"Question: {question}\n\nSources:\n{context}",
    )


def compare_summary(a_name, a_rows, b_name, b_rows):
    def block(name, rows):
        lines = [f"- {r.short_title} ({r.instrument_type}; {r.status}; {r.date.year if pd.notna(r.date) else 'n/a'})" for r in rows.head(25).itertuples()]
        return f"{name}:\n" + "\n".join(lines)
    return llm.chat(
        "You are an AI policy analyst. Compare the two jurisdictions' approaches to AI regulation in 4-5 sentences: "
        "binding vs voluntary, comprehensive vs sectoral, and notable gaps. Use only the lists given.",
        block(a_name, a_rows) + "\n\n" + block(b_name, b_rows),
    )
