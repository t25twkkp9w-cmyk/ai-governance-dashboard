# AI Governance Dashboard

One Streamlit app with two connected parts:

1. **AI Incident Risk Tracker**: 7,718 real-world AI incidents, each tagged with the **company alleged to be responsible** and classified against the **EU AI Act**, **NIST AI RMF 1.0** and **ISO/IEC 42001:2023**, with on-demand risk briefings.
2. **AI Policy & Regulation Explorer**: 2,585 AI laws, bills, strategies and guidance documents across 110+ countries, the EU and other blocs, and all US states, with a world map, timeline, side-by-side jurisdiction comparison and an "ask the policies" search.

The two parts are linked: the policy map plots each country's reported AI incidents against the binding AI rules it has in effect.

> Classifications are **indicative, rule-based triage**, not legal determinations. "Responsible company" means the developer or deployer **alleged** in the incident report. Not legal advice.

## Quick start

```bash
uv sync
uv run streamlit run app.py
```

The data is already in `data/`, so the app works immediately with **no API key**.

**Optional AI features:** copy `.env.example` to `.env` and add a `GROQ_API_KEY` (free tier at console.groq.com) or an `OPENAI_API_KEY`. This turns on AI executive summaries in briefings, cited answers in "Ask the policies", and AI-written jurisdiction comparisons.

## Look and feel

The app follows the dashboard design: a cool off-white page with white cards, a dark-grey sidebar, IBM Plex Sans with IBM Plex Mono for numbers, and one blue scale for charts (darker = more serious; orange marks the second series). Colours live in `theme.py` and `.streamlit/config.toml`; change `ACCENT` / `primaryColor` there to re-brand. The sidebar theme needs Streamlit 1.46 or newer.

## Tabs

| Tab | What it shows |
|---|---|
| **Overview** | Incidents per month, high-risk share, harm types, sectors |
| **Framework mapping** | EU AI Act tiers (with the Article/Annex that triggered each), NIST characteristics and functions, ISO 42001 controls, harm × tier cross-walk |
| **Companies** | Companies with the most incidents, who gets named (company, government, individual, unknown actors), company × harm-type heatmap, a risk scorecard, and a per-company deep dive |
| **Incident explorer** | Searchable, downloadable table of every incident |
| **Risk briefing** | Daily / weekly / monthly / quarterly briefing, downloadable as Markdown |
| **Policy map** | World map and US-states map (all instruments, binding in effect, or proposed); policy types by region; incidents vs regulation scatter; jurisdiction status summaries |
| **Policy timeline** | Instruments per year by level, US state bills by outcome, cumulative binding rules, topics over time, milestone laws |
| **Compare jurisdictions** | Pick any two (e.g. EU vs China, California vs Texas): counts, topic coverage matrix, instruments side by side, optional AI comparison |
| **Ask the policies** | Natural-language search over all instruments, with an optional cited AI answer |

The sidebar has separate **incident filters** (years, company, EU tier, harm type, severity, source) and **policy filters** (level, instrument type, status, region, topic, binding only).

## Risk briefings from the terminal

```bash
uv run python briefing.py --period weekly
uv run python briefing.py --period quarterly --as-of 2026-06-30 > q2_briefing.md
uv run python briefing.py --period monthly --llm    # adds an AI executive summary
```

Samples are in `briefings/`.

## Data sources

| Dataset | Used for | Licence |
|---|---|---|
| [AI Incident Database (AIID)](https://incidentdatabase.ai), Responsible AI Collaborative: full snapshot in `data/raw/aiid/` | 1,712 incidents (AIID #1–#1724, to 28 Sep 2026) with full descriptions, alleged deployer, developer and harmed parties, MIT risk classification and news-report counts | CC BY-SA 4.0 |
| [AIAAIC Repository](https://www.aiaaic.org/aiaaic-repository) | 1,499 incidents | CC BY-SA 4.0 |
| [OECD AI Incidents and Hazards Monitor](https://oecd.ai/en/incidents) | 3,940 incidents | See OECD.AI terms |
| [MIT AI Risk Repository](https://airisk.mit.edu) | Risk domain and intent for AIID incidents; EU AI Act tier labels | CC BY 4.0 |
| [GenAI & Agentic AI Incidents](https://github.com/emmanuelgjr/genai_agentic_incidents) | The open corpus that combines the four sources above (plus 721 research/threat reports) | CC BY 4.0 |
| [AI Policy Tracker](https://github.com/8h45k4r/aipolicytracker) | Worldwide policies + jurisdiction summaries | Data CC BY 4.0 |
| [Global AI Atlas (GAIA)](https://github.com/artvana/global-ai-atlas) | US federal and state laws and bills, more national laws | MIT |

**Licence note:** AIID and AIAAIC content is CC BY-SA 4.0, so `data/incidents_classified.csv` (which includes their text) should be shared under CC BY-SA 4.0 with attribution if you publish it.

## Rebuilding the data

```bash
git clone --depth 1 https://github.com/emmanuelgjr/genai_agentic_incidents.git
git clone --depth 1 https://github.com/8h45k4r/aipolicytracker.git
git clone --depth 1 https://github.com/artvana/global-ai-atlas.git
# Optional: refresh the AI Incident Database snapshot from incidentdatabase.ai ("Download Complete Database")
# and copy incidents.csv, classifications_MIT.csv and duplicates.csv into data/raw/aiid/
uv run python classify.py genai_agentic_incidents/data/incidents.json
uv run python build_policies.py aipolicytracker global-ai-atlas
```

## How it works

**Incidents (`classify.py`, `frameworks.py`, `companies.py`)**
1. **Harm type**: keyword rules in priority order, falling back to the source's attack-vector label.
2. **EU AI Act tier**: Art. 5 prohibited practices, the Art. 2(3) military exclusion, Art. 50 transparency, Annex I/III high-risk domains, Chapter V general-purpose AI, then the MIT AI Risk Repository label if nothing fires.
3. **NIST AI RMF**: trustworthiness characteristics from keyword rules plus harm type; function from the source's NIST subcategories.
4. **ISO/IEC 42001**: harm type maps to Annex A controls; supplier mentions add A.10.3, high-risk systems add A.5.2.
5. **Responsible company**: for AIID incidents, the first named company among AIID's *alleged deployers*, then its *alleged developers* (both are also shown separately, with the harmed parties). For other sources, the database's deployer/developer field, then a known company named in the title. Products roll up to their company (ChatGPT → OpenAI, Instagram → Meta, Grok → xAI). Government bodies are labelled as such. Named private individuals are never shown as the responsible party.
6. **Positive-use stories** (e.g. "AI system prevents drownings") are flagged and hidden by default.

**Policies (`build_policies.py`, `policy.py`)**
- The two policy datasets are merged and de-duplicated, then instrument types, statuses and topics are normalised.
- "Ask the policies" uses BM25 keyword search (no API needed). With a key, an LLM answers using only the retrieved instruments and cites them.
- Incidents are matched to countries by jurisdiction tag and country names in the title.

## Known limitations

- Keyword rules miss nuance. About a fifth of incidents (8% of AIID ones, which have full descriptions) get harm type "Other", and about a third have no identifiable responsible party (mostly OECD entries with title-only text).
- US state bills dominate the policy count (about 2,200 of 2,585). Map, region and timeline views separate them out.
- Policy dates are adoption or effective dates where known, otherwise the latest legislative action; about 28% of instruments have no usable date.
- OECD, AIAAIC and research data run through mid-July 2026; the AIID snapshot runs to 28 September 2026, so August–September counts reflect AIID only. Briefings flag partial periods.
- **Cross-source duplicates:** 154 incidents recorded by more than one database were merged. 114 AIID incidents also in AIAAIC (99) or OECD (15) keep the AIID record; 40 OECD entries that duplicate an AIAAIC incident keep the AIAAIC record (and take OECD's exact date where AIAAIC had only a year). The other source is linked in "Also in". Candidates were found by date window and title/description similarity, then every pair was confirmed by hand; the confirmed lists are `data/raw/aiid/cross_source_matches.csv` and `data/raw/aiaaic_oecd_matches.csv`. Pairs worded too differently to surface as candidates may remain.

## Project structure

```text
app.py              Streamlit dashboard (9 tabs)
briefing.py         Risk briefing engine + CLI
classify.py         Builds data/incidents_classified.csv
frameworks.py       EU AI Act / NIST / ISO 42001 rules
companies.py        Responsible-company extraction
aiid.py             AI Incident Database snapshot loader
build_policies.py   Builds data/policies.csv and data/jurisdictions.csv
policy.py           Policy search, comparison, incident-country matching
llm.py              Optional Groq/OpenAI access
theme.py            Colours, fonts, sidebar and chart styling (Plotly template + CSS)
.streamlit/config.toml  Streamlit theme (page, sidebar and accent colours)
iso_codes.py        Country and US state codes for maps
data/               Generated datasets (data/raw/aiid/ holds the AIID snapshot)
briefings/          Sample briefings
tests/              Tests (uv run pytest)
```
