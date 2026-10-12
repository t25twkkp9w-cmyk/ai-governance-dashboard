"""
AI Governance Dashboard — AI Incident Risk Tracker + AI Policy & Regulation Explorer.

Run:  uv run streamlit run app.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

import briefing as br
import frameworks as fw
import llm
import policy as pol
import theme
from iso_codes import US_STATES

load_dotenv()
DATA = Path(__file__).parent / "data"

# Ordinal blue ramp for EU AI Act tiers (light -> dark = less -> more restricted);
# the military exclusion is not on that scale, so it is neutral gray.
TIER_COLORS = {
    "Minimal": "#86b6ef",
    "Limited / transparency (Art. 50)": "#5598e7",
    "GPAI obligations (Ch. V)": "#2a78d6",
    "High-risk (Annex I/III)": "#1c5cab",
    "Unacceptable (Art. 5)": "#0d366b",
    "Out of scope (military, Art. 2(3))": "#a3a29c",
}
TIER_ORDER = list(TIER_COLORS)
SERIES = theme.SERIES   # blue, orange, green, gold
BAR = theme.ACCENT
SEQ = theme.SEQ         # sequential blue, light -> dark
LEVEL_ORDER = ["National", "Subnational", "Supranational", "International"]


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@st.cache_data
def load_incidents() -> pd.DataFrame:
    return br.load(DATA / "incidents_classified.csv")


@st.cache_data
def load_policy_data():
    return pol.load_policies(DATA / "policies.csv"), pol.load_jurisdictions(DATA / "jurisdictions.csv")


@st.cache_resource
def policy_index(_df, n):  # n busts the cache when the filtered set changes size
    return pol.PolicyIndex(_df)


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------
def bar(series: pd.Series, title: str, unit="incidents", height=None):
    d = series.sort_values().reset_index()
    d.columns = ["label", "count"]
    fig = px.bar(d, x="count", y="label", orientation="h", text="count",
                 color_discrete_sequence=[BAR], height=height or max(260, 34 * len(d) + 80))
    fig.update_traces(textposition="outside", cliponaxis=False,
                      hovertemplate="%{y}: %{x:,} " + unit + "<extra></extra>")
    fig.update_layout(title=title, xaxis_title=unit.capitalize(), yaxis_title=None, margin=dict(l=0, r=30, t=50, b=10))
    return fig


def heatmap(table: pd.DataFrame, height=460, unit="incidents"):
    fig = px.imshow(table, text_auto=True, aspect="auto", color_continuous_scale=SEQ)
    fig.update_traces(hovertemplate="%{y} · %{x}: %{z:,} " + unit + "<extra></extra>")
    fig.update_layout(xaxis_title=None, yaxis_title=None, coloraxis_showscale=False, height=height, margin=dict(t=10))
    return fig


def show(fig):
    st.plotly_chart(fig, use_container_width=True, theme=None)


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
def incident_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Incident filters")
    st.sidebar.caption("Apply to the five incident tabs.")
    years = sorted(int(y) for y in df["year"].dropna().unique())
    lo, hi = st.sidebar.select_slider("Years", options=years, value=(max(years[0], 2015), years[-1]))
    out = df[df["year"].between(lo, hi)]
    top_cos = out.loc[out["responsible_company"] != "", "responsible_company"].value_counts().index.tolist()
    for col, label, opts in [
        ("responsible_company", "Company", top_cos),
        ("eu_ai_act_tier", "EU AI Act tier", [t for t in TIER_ORDER if t in out["eu_ai_act_tier"].unique()]),
        ("harm_type", "Harm type", sorted(out["harm_type"].unique())),
        ("severity", "Severity", ["Critical", "High", "Medium", "Low"]),
        ("source", "Source database", sorted(out["source"].unique())),
    ]:
        pick = st.sidebar.multiselect(label, opts)
        if pick:
            out = out[out[col].isin(pick)]
    if st.sidebar.checkbox("Hide positive-use stories", value=True,
                           help="The OECD monitor also logs beneficial uses of AI; hide them to focus on harms."):
        out = out[out["story_type"] != "Positive use / benefit"]
    q = st.sidebar.text_input("Search incident titles")
    if q:
        out = out[out["title"].str.contains(q, case=False, na=False, regex=False)]
    st.sidebar.caption(f"{len(out):,} of {len(df):,} incidents")
    return out


def policy_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.divider()
    st.sidebar.header("Policy filters")
    st.sidebar.caption("Apply to the policy map, timeline and comparison tabs.")
    out = df
    for col, label, opts in [
        ("level", "Level", [l for l in LEVEL_ORDER if l in df["level"].unique()]),
        ("instrument_type", "Instrument type", sorted(df["instrument_type"].unique())),
        ("status", "Status", sorted(df["status"].unique())),
        ("region", "Region", sorted(r for r in df["region"].unique() if r)),
    ]:
        pick = st.sidebar.multiselect(label, opts, key=f"pol_{col}")
        if pick:
            out = out[out[col].isin(pick)]
    topic = st.sidebar.selectbox("Topic", ["All topics"] + pol.TOPICS, key="pol_topic")
    if topic != "All topics":
        out = out[pol.has_topic(out, topic)]
    if st.sidebar.checkbox("Binding instruments only", key="pol_binding"):
        out = out[out["binding"]]
    st.sidebar.caption(f"{len(out):,} of {len(df):,} instruments")
    return out


# ---------------------------------------------------------------------------
# Incident tabs
# ---------------------------------------------------------------------------
def overview(d: pd.DataFrame):
    high = d["eu_ai_act_tier"].isin(br.HIGH_TIERS)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Incidents", f"{len(d):,}")
    c2.metric("Unacceptable + high-risk", f"{high.sum():,}", f"{high.mean():.0%} of total" if len(d) else None, delta_color="off")
    c3.metric("Critical severity", f"{(d['severity'] == 'Critical').sum():,}")
    c4.metric("Companies named", f"{d.loc[d['responsible_company'] != '', 'responsible_company'].nunique():,}")

    m = d[d["date_precision"].isin(["day", "month"])].copy()
    m["month"] = m["date"].dt.to_period("M").dt.to_timestamp()
    trend = pd.DataFrame({
        "All incidents": m.groupby("month").size(),
        "Unacceptable + high-risk": m[m["eu_ai_act_tier"].isin(br.HIGH_TIERS)].groupby("month").size(),
    }).fillna(0).reset_index().melt("month", var_name="series", value_name="count")
    fig = px.line(trend, x="month", y="count", color="series", color_discrete_sequence=SERIES, title="Incidents per month")
    fig.update_traces(line_width=2, hovertemplate="%{x|%b %Y}: %{y:,}<extra>%{fullData.name}</extra>")
    fig.update_layout(hovermode="x unified", xaxis_title=None, yaxis_title="Incidents",
                      legend=dict(orientation="h", y=1.12, title=None), margin=dict(t=70))
    show(fig)
    st.caption("Monthly counts use incidents with a day- or month-precise date. Recent months are still being backfilled by the source databases.")

    a, b = st.columns(2)
    a.plotly_chart(bar(d["harm_type"].value_counts(), "Harm type"), use_container_width=True, theme=None)
    sectors = d.loc[d["sector"] != "Unknown", "sector"].value_counts().head(10)
    b.plotly_chart(bar(sectors, "Top sectors (where tagged)"), use_container_width=True, theme=None)


def frameworks_tab(d: pd.DataFrame):
    st.subheader("EU AI Act risk tier")
    t = d["eu_ai_act_tier"].value_counts().reindex(TIER_ORDER).dropna().reset_index()
    t.columns = ["tier", "count"]
    fig = px.bar(t, x="count", y="tier", orientation="h", color="tier", text="count",
                 color_discrete_map=TIER_COLORS, category_orders={"tier": TIER_ORDER[::-1]})
    fig.update_traces(textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x:,}<extra></extra>")
    fig.update_layout(showlegend=False, xaxis_title="Incidents", yaxis_title=None, height=330, margin=dict(t=10, r=30))
    show(fig)
    with st.expander("Which Article / Annex triggered the tier?"):
        st.dataframe(d.groupby(["eu_ai_act_tier", "eu_ai_act_basis"]).size().rename("incidents")
                     .reset_index().sort_values("incidents", ascending=False), hide_index=True, use_container_width=True)

    a, b = st.columns(2)
    with a:
        st.subheader("NIST AI RMF")
        show(bar(d["nist_characteristic"].value_counts(), "Trustworthiness characteristic at stake"))
        show(bar(d["nist_function"].value_counts(), "Core function most implicated", height=260))
    with b:
        st.subheader("ISO/IEC 42001 Annex A")
        ctrl = d["iso42001_controls"].str.split("; ").explode().value_counts()
        ctrl.index = [f"{k} {fw.ISO_CONTROLS[k]}" for k in ctrl.index]
        show(bar(ctrl, "Controls implicated (an incident can map to several)"))

    st.subheader("MIT AI Risk Repository domain")
    mit = d[d["mit_risk_domain"] != ""]
    l, r = st.columns([1.4, 1])
    l.plotly_chart(bar(mit["mit_risk_domain"].value_counts(), f"Risk domain ({len(mit):,} incidents classified by MIT / AIID)"),
                   use_container_width=True, theme=None)
    intent = mit.loc[mit["mit_intent"] != "", "mit_intent"].value_counts()
    if len(intent):
        r.plotly_chart(bar(intent, "Intentional or unintentional harm?", height=260), use_container_width=True, theme=None)

    st.subheader("Cross-walk: harm type × EU AI Act tier")
    xt = pd.crosstab(d["harm_type"], d["eu_ai_act_tier"]).reindex(columns=[c for c in TIER_ORDER if c in d["eu_ai_act_tier"].unique()])
    show(heatmap(xt))


def companies_tab(d: pd.DataFrame):
    st.caption("The organisation **alleged** in incident reports to have developed or deployed the AI system. "
               "It comes from the source database's deployer/developer field, or a company named in the title. "
               "An allegation is not a finding of fault.")
    named = d[d["responsible_company"] != ""]
    corp = named[named["entity_type"] == "Company"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Incidents with a named party", f"{len(named):,}", f"{len(named) / max(len(d), 1):.0%} of total", delta_color="off")
    c2.metric("Companies", f"{corp['responsible_company'].nunique():,}")
    c3.metric("Government / public bodies", f"{(d['entity_type'] == 'Government / public body').sum():,} incidents")
    c4.metric("Top company", corp["responsible_company"].value_counts().index[0] if len(corp) else "–")

    a, b = st.columns([1.1, 1])
    a.plotly_chart(bar(corp["responsible_company"].value_counts().head(15), "Companies with the most incidents"), use_container_width=True, theme=None)
    b.plotly_chart(bar(d["entity_type"].value_counts(), "Who is named as responsible?", height=330), use_container_width=True, theme=None)

    top = corp["responsible_company"].value_counts().head(12).index
    st.subheader("What kind of risk each company is linked to")
    show(heatmap(pd.crosstab(corp.loc[corp["responsible_company"].isin(top), "responsible_company"],
                             corp.loc[corp["responsible_company"].isin(top), "harm_type"]).reindex(top), height=480))

    st.subheader("Company risk scorecard")
    score = corp.groupby("responsible_company").agg(
        incidents=("id", "size"),
        high_or_unacceptable=("eu_ai_act_tier", lambda s: int(s.isin(br.HIGH_TIERS).sum())),
        critical=("severity", lambda s: int((s == "Critical").sum())),
        avg_risk=("risk_score", "mean"),
        top_harm=("harm_type", lambda s: s.mode().iat[0]),
        top_nist=("nist_characteristic", lambda s: s.mode().iat[0]),
        latest=("date", "max"),
    ).sort_values("incidents", ascending=False).head(40).reset_index()
    st.dataframe(score, hide_index=True, use_container_width=True, column_config={
        "responsible_company": "Company",
        "high_or_unacceptable": st.column_config.NumberColumn("EU high/unacceptable"),
        "avg_risk": st.column_config.ProgressColumn("Avg risk", min_value=0, max_value=100, format="%.0f"),
        "latest": st.column_config.DateColumn("Latest incident", format="YYYY-MM-DD"),
    })

    st.subheader("Company deep dive")
    pick = st.selectbox("Company", corp["responsible_company"].value_counts().index.tolist())
    if pick:
        c = corp[corp["responsible_company"] == pick]
        k1, k2, k3 = st.columns(3)
        k1.metric("Incidents", len(c))
        k2.metric("Most common harm", c["harm_type"].mode().iat[0])
        k3.metric("Main ISO 42001 control", c["iso42001_primary"].mode().iat[0] + " " + fw.ISO_CONTROLS[c["iso42001_primary"].mode().iat[0]])
        l, r = st.columns(2)
        t = c["eu_ai_act_tier"].value_counts().reindex(TIER_ORDER).dropna()
        l.plotly_chart(bar(t, "EU AI Act tiers", height=300), use_container_width=True, theme=None)
        yearly = c.groupby("year").size()
        fig = px.bar(yearly.reset_index(name="n"), x="year", y="n", color_discrete_sequence=[BAR], title="Incidents per year", height=300)
        fig.update_traces(hovertemplate="%{x}: %{y} incidents<extra></extra>")
        fig.update_layout(xaxis_title=None, yaxis_title="Incidents", margin=dict(t=50))
        r.plotly_chart(fig, use_container_width=True, theme=None)
        harmed = c["harmed_parties"].str.split("; ").explode()
        harmed = harmed[harmed.fillna("") != ""].value_counts().head(8)
        if len(harmed):
            st.markdown("**Most often harmed (AI Incident Database):** " + ", ".join(f"{k} ({v})" for k, v in harmed.items()))
        st.dataframe(c.sort_values("date", ascending=False)[["date", "title", "alleged_deployer", "alleged_developer", "harm_type", "eu_ai_act_tier", "severity", "url"]],
                     hide_index=True, use_container_width=True, column_config={
                         "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                         "url": st.column_config.LinkColumn("Source", display_text="open")})


def explorer(d: pd.DataFrame):
    cols = ["date", "title", "responsible_company", "alleged_deployer", "alleged_developer", "harmed_parties", "severity",
            "risk_score", "harm_type", "eu_ai_act_tier", "eu_ai_act_basis", "nist_characteristic", "nist_function",
            "iso42001_controls", "mit_risk_domain", "report_count", "sector", "source", "also_reported_by", "url"]
    st.dataframe(
        d.sort_values(["risk_score", "date"], ascending=False)[cols],
        hide_index=True, use_container_width=True, height=520,
        column_config={
            "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
            "responsible_company": "Company (alleged)",
            "alleged_deployer": "Alleged deployer", "alleged_developer": "Alleged developer",
            "harmed_parties": "Harmed or nearly harmed", "mit_risk_domain": "MIT risk domain",
            "also_reported_by": st.column_config.TextColumn("Also in", help="Same incident recorded by another database (merged)"),
            "report_count": st.column_config.NumberColumn("News reports", help="Reports linked in the AI Incident Database"),
            "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=100, format="%d"),
            "url": st.column_config.LinkColumn("Source", display_text="open"),
        },
    )
    st.download_button("Download filtered CSV", d.to_csv(index=False), "ai_incidents_filtered.csv", "text/csv")


def briefing_tab(d: pd.DataFrame):
    st.write("Generate a risk briefing for any period. Incident filters in the sidebar apply, so you can brief on one company, sector or harm type.")
    c1, c2, c3 = st.columns([1, 1, 1.4])
    period = c1.radio("Period", br.PERIODS, index=1, horizontal=True)
    latest = br.latest_date(d) if len(d) else pd.Timestamp.today()
    as_of = c2.date_input("As of", value=latest.date() if pd.notna(latest) else None)
    has_key = bool(llm.provider())
    use_llm = c3.toggle("Add AI executive summary", value=False, disabled=not has_key,
                        help=None if has_key else "Add GROQ_API_KEY or OPENAI_API_KEY to .env to enable.")
    if st.button("Generate briefing", type="primary"):
        with st.spinner("Building briefing…"):
            md, _ = br.generate(d, period, as_of, use_llm)
        st.session_state["briefing_md"] = md
    if md := st.session_state.get("briefing_md"):
        st.divider()
        st.markdown(md)
        st.download_button("Download as Markdown", md, f"ai_risk_briefing_{period}.md", "text/markdown")


# ---------------------------------------------------------------------------
# Policy tabs
# ---------------------------------------------------------------------------
def policy_map_tab(p: pd.DataFrame, jur: pd.DataFrame, incidents: pd.DataFrame):
    in_effect = p["in_effect"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Policy instruments", f"{len(p):,}")
    c2.metric("Binding & in effect", f"{(p['binding'] & in_effect).sum():,}")
    c3.metric("Countries with an instrument", f"{p.loc[p['level'] == 'National', 'country'].nunique():,}")
    c4.metric("US state instruments", f"{(p['level'] == 'Subnational').sum():,}")

    view = st.radio("Map", ["World", "US states"], horizontal=True, label_visibility="collapsed")
    metric = st.radio("Colour by", ["All instruments", "Binding & in effect", "Proposed"], horizontal=True)
    if view == "World":
        nat = p[(p["level"] == "National") & (p["iso3"] != "")]
        g = nat.groupby(["iso3", "country"]).agg(
            all=("id", "size"), binding=("binding", lambda s: int((s & nat.loc[s.index, "in_effect"]).sum())),
            proposed=("status", lambda s: int((s == "Proposed / in consultation").sum())),
            latest=("short_title", "first")).reset_index()
        col = {"All instruments": "all", "Binding & in effect": "binding", "Proposed": "proposed"}[metric]
        fig = px.choropleth(g, locations="iso3", color=col, hover_name="country", color_continuous_scale=SEQ[1:],
                            hover_data={"iso3": False, "all": True, "binding": True, "proposed": True, "latest": True},
                            labels={"all": "Instruments", "binding": "Binding & in effect", "proposed": "Proposed", "latest": "Most recent"})
        fig.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth")
        st.caption("National instruments only. The US map shows state laws; the EU and other blocs are listed under Supranational.")
    else:
        st_ = p[p["level"] == "Subnational"].copy()
        st_["abbr"] = st_["state"].map(US_STATES)
        st_ = st_.dropna(subset=["abbr"])
        g = st_.groupby(["abbr", "state"]).agg(
            all=("id", "size"), binding=("binding", lambda s: int((s & st_.loc[s.index, "in_effect"]).sum())),
            proposed=("status", lambda s: int((s == "Proposed / in consultation").sum()))).reset_index()
        col = {"All instruments": "all", "Binding & in effect": "binding", "Proposed": "proposed"}[metric]
        fig = px.choropleth(g, locations="abbr", locationmode="USA-states", scope="usa", color=col, hover_name="state",
                            color_continuous_scale=SEQ[1:], hover_data={"abbr": False, "all": True, "binding": True, "proposed": True},
                            labels={"all": "Instruments", "binding": "Binding & in effect", "proposed": "Proposed"})
    fig.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=0), coloraxis_colorbar=dict(title=None))
    show(fig)

    st.subheader("Policy types by region")
    nonstate = p[p["level"] != "Subnational"]
    show(heatmap(pd.crosstab(nonstate["region"].replace("", "Unassigned"), nonstate["instrument_type"]), height=320, unit="instruments"))
    st.caption("National, bloc and international instruments. US state bills are left out here so they don't swamp the Americas row; see the US states map.")

    st.subheader("Does regulation follow incidents?")
    sc = pol.country_scorecard(p, incidents)
    sc = sc[(sc["incidents"] > 0) | (sc["instruments"] > 0)]
    sc = sc[sc["country"] != "United States"]  # US dwarfs every axis; see the US states map
    fig = px.scatter(sc, x="incidents", y="binding_in_effect", size="instruments", hover_name="country", size_max=28,
                     color_discrete_sequence=[BAR], labels={"incidents": "Reported AI incidents mentioning the country",
                                                           "binding_in_effect": "Binding AI instruments in effect",
                                                           "instruments": "All instruments"})
    fig.update_traces(marker=dict(line=dict(width=2, color="white"), opacity=0.85))
    for _, r in sc.nlargest(6, "incidents").iterrows():
        fig.add_annotation(x=r["incidents"], y=r["binding_in_effect"], text=r["country"], showarrow=False, yshift=14, font=dict(size=11))
    fig.update_layout(height=420, margin=dict(t=10))
    show(fig)
    st.caption("Incidents are matched to countries by jurisdiction tag and country names in the title. The United States "
               f"is left off the chart for scale ({int(pol.country_scorecard(p, incidents).set_index('country').loc['United States', 'incidents']):,} incidents).")

    with st.expander("Jurisdiction status summaries"):
        pick = st.selectbox("Jurisdiction", jur.sort_values("instruments", ascending=False)["jurisdiction"].tolist())
        row = jur[jur["jurisdiction"] == pick].iloc[0]
        st.write(row["status_summary"] or "No summary recorded.")


def policy_timeline_tab(p: pd.DataFrame):
    dated = p[p["year"].between(2016, 2026)].copy()
    dated["year"] = dated["year"].astype(int)
    st.caption(f"{len(dated):,} of {len(p):,} instruments have a usable date (adoption, effective date or latest legislative action).")
    levels = ["National", "Supranational", "International"]
    y = dated[dated["level"].isin(levels)].groupby(["year", "level"]).size().unstack(fill_value=0).reindex(
        index=range(2016, 2027), columns=levels, fill_value=0).reset_index().melt("year", var_name="level", value_name="n")
    fig = px.line(y, x="year", y="n", color="level", markers=True, color_discrete_sequence=SERIES,
                  category_orders={"level": levels}, title="National, bloc and international instruments per year")
    fig.update_traces(line_width=2, marker_size=8, hovertemplate="%{x}: %{y:,}<extra>%{fullData.name}</extra>")
    fig.update_layout(hovermode="x unified", xaxis_title=None, yaxis_title="Instruments", legend=dict(orientation="h", y=1.12, title=None), margin=dict(t=70))
    show(fig)

    states = dated[dated["level"] == "Subnational"].copy()
    if len(states):
        states["outcome"] = states["status"].replace({"Enacted, not yet effective": "In force / adopted",
                                                      "Superseded / repealed": "Failed / vetoed / withdrawn"})
        order = ["In force / adopted", "Proposed / in consultation", "Failed / vetoed / withdrawn"]
        sy = states.groupby(["year", "outcome"]).size().reset_index(name="n")
        fig = px.bar(sy, x="year", y="n", color="outcome", barmode="group", color_discrete_sequence=SERIES,
                     category_orders={"outcome": order}, title="US state AI bills by year and outcome")
        fig.update_traces(hovertemplate="%{x}: %{y:,}<extra>%{fullData.name}</extra>", marker_line_width=0)
        fig.update_layout(xaxis_title=None, yaxis_title="Bills / laws", legend=dict(orientation="h", y=1.12, title=None),
                          margin=dict(t=70), bargap=0.25, bargroupgap=0.08)
        show(fig)
        st.caption("Dated by enactment, or by latest legislative action for bills still moving or that died.")

    binding = dated[dated["binding"] & dated["in_effect"]]
    cum = binding.groupby("year").size().reindex(range(2016, 2027), fill_value=0).cumsum().reset_index(name="n")
    cum.columns = ["year", "n"]
    fig = px.area(cum, x="year", y="n", color_discrete_sequence=[BAR], title="Cumulative binding AI instruments in effect")
    fig.update_traces(line_width=2, hovertemplate="%{x}: %{y:,} in effect<extra></extra>")
    fig.update_layout(xaxis_title=None, yaxis_title="Instruments", margin=dict(t=50))
    show(fig)

    st.subheader("Topics over time")
    t = dated.assign(topic=dated["topics"].str.split("; ")).explode("topic", ignore_index=True)
    show(heatmap(pd.crosstab(t["topic"], t["year"]), height=480, unit="instruments"))

    st.subheader("Milestones: national and bloc-level binding laws")
    ms = p[(p["level"].isin(["National", "Supranational"])) & p["binding"] & p["in_effect"] & p["date"].notna()]
    st.dataframe(ms.sort_values("date")[["date", "jurisdiction", "short_title", "instrument_type", "topics", "url"]],
                 hide_index=True, use_container_width=True, height=400, column_config={
                     "date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                     "short_title": "Instrument", "url": st.column_config.LinkColumn("Source", display_text="open")})


def compare_tab(p: pd.DataFrame, jur: pd.DataFrame, incidents: pd.DataFrame):
    counts = p["jurisdiction"].value_counts()
    options = counts.index.tolist()
    default_a = options.index("European Union") if "European Union" in options else 0
    default_b = options.index("China") if "China" in options else 1
    a_col, b_col = st.columns(2)
    a = a_col.selectbox("Jurisdiction A", options, index=default_a)
    b = b_col.selectbox("Jurisdiction B", options, index=default_b)
    inc_c = pol.incident_countries(incidents).value_counts()

    def facts(name):
        rows = p[p["jurisdiction"] == name].sort_values("date", ascending=False)
        summary = jur.loc[jur["jurisdiction"] == name, "status_summary"]
        country = rows["country"].iloc[0] if len(rows) and rows["country"].iloc[0] else name
        return rows, (summary.iloc[0] if len(summary) else ""), int(inc_c.get(country, 0))

    ra, sa, ia = facts(a)
    rb, sb, ib = facts(b)
    for col, name, rows, summ, inc in [(a_col, a, ra, sa, ia), (b_col, b, rb, sb, ib)]:
        with col:
            st.markdown(f"#### {name}")
            m1, m2, m3 = st.columns(3)
            m1.metric("Instruments", len(rows))
            m2.metric("Binding in effect", int((rows["binding"] & rows["in_effect"]).sum()))
            m3.metric("Incidents mentioning it", inc)
            if summ:
                st.caption(summ[:600] + ("…" if len(summ) > 600 else ""))

    st.subheader("Topic coverage")
    st.caption("● binding and in effect · ◐ non-binding, proposed or not yet effective · – nothing recorded")

    def mark(rows, topic):
        t = rows[pol.has_topic(rows, topic)]
        if (t["binding"] & t["in_effect"]).any():
            return "● Binding"
        if len(t[t["status"] != "Failed / vetoed / withdrawn"]):
            return "◐ Partial"
        return "–"

    cov = pd.DataFrame({"Topic": pol.TOPICS, a: [mark(ra, t) for t in pol.TOPICS], b: [mark(rb, t) for t in pol.TOPICS]})
    st.dataframe(cov, hide_index=True, use_container_width=True, height=36 * len(cov) + 40)

    st.subheader("Instruments side by side")
    l, r = st.columns(2)
    cols = ["date", "short_title", "instrument_type", "status", "url"]
    cfg = {"date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"), "short_title": "Instrument",
           "url": st.column_config.LinkColumn("Source", display_text="open")}
    l.dataframe(ra[cols], hide_index=True, use_container_width=True, column_config=cfg)
    r.dataframe(rb[cols], hide_index=True, use_container_width=True, column_config=cfg)

    if llm.provider() and st.button("Write an AI comparison"):
        with st.spinner("Comparing…"):
            st.markdown(pol.compare_summary(a, ra, b, rb))


def ask_tab(p: pd.DataFrame):
    st.write("Ask a question about AI laws and policies. The app finds the most relevant instruments; with an API key it also writes a cited answer.")
    examples = ["Which laws regulate deepfakes in elections?", "Rules for AI in hiring decisions",
                "Frontier model safety requirements", "How is facial recognition by police regulated?"]
    cols = st.columns(len(examples))
    for c, ex in zip(cols, examples):
        if c.button(ex, use_container_width=True):
            st.session_state["policy_q"] = ex
    q = st.text_input("Your question", key="policy_q", placeholder="e.g. What transparency rules apply to chatbots?")
    scope = st.multiselect("Limit to jurisdictions (optional)", p["jurisdiction"].value_counts().index.tolist())
    if not q:
        return
    hits = policy_index(p, len(p)).search(q, k=8, jurisdictions=scope or None)
    if llm.provider():
        with st.spinner("Writing a cited answer…"):
            ans = pol.answer(q, hits)
        st.markdown(ans)
    else:
        st.info("Add GROQ_API_KEY or OPENAI_API_KEY to .env for a written, cited answer. The matching instruments are below.")
    st.markdown("**Sources**")
    for n, r in enumerate(hits.itertuples(), 1):
        badge = "Binding" if r.binding else "Non-binding"
        date = r.date.strftime("%Y-%m-%d") if pd.notna(r.date) else "date n/a"
        with st.container(border=True):
            st.markdown(f"**[{n}] {r.short_title}** · {r.jurisdiction}  \n{r.instrument_type} · {r.status} · {badge} · {date}")
            if r.summary:
                st.caption(r.summary[:400] + ("…" if len(r.summary) > 400 else ""))
            if r.url:
                st.markdown(f"[Official source]({r.url})")
    st.caption("Not legal advice. Check the official source before relying on any instrument.")


# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="AI Governance Dashboard", page_icon=":shield:", layout="wide")
    theme.apply()
    theme.sidebar_brand()
    theme.page_header(
        "AI Incident Risk Tracker · AI Policy &amp; Regulation Explorer",
        "AI Governance Dashboard",
        "Real-world AI incidents mapped to the EU AI Act, NIST AI RMF 1.0 and ISO/IEC 42001, alongside the AI laws "
        "and policies being written in response. Mappings are indicative triage, not legal advice.",
    )
    if not (DATA / "incidents_classified.csv").exists() or not (DATA / "policies.csv").exists():
        st.error("Data files missing. Run `uv run python classify.py …` and `uv run python build_policies.py …` (see README).")
        st.stop()
    incidents_all = load_incidents()
    policies_all, jur = load_policy_data()
    d = incident_filters(incidents_all)
    p = policy_filters(policies_all)
    latest = incidents_all.loc[incidents_all["date_precision"] == "day"].groupby("source")["date"].max()
    theme.sidebar_footer([
        ("AIID data through", f"{latest.get('AIID'):%d %b %Y}" if "AIID" in latest else "n/a"),
        ("OECD · AIAAIC through", f"{latest.get('OECD AIM'):%d %b %Y}" if "OECD AIM" in latest else "n/a"),
    ])

    tabs = st.tabs(["Overview", "Framework mapping", "Companies", "Incident explorer", "Risk briefing",
                    "Policy map", "Policy timeline", "Compare jurisdictions", "Ask the policies"])
    with tabs[0]:
        overview(d)
    with tabs[1]:
        frameworks_tab(d)
    with tabs[2]:
        companies_tab(d)
    with tabs[3]:
        explorer(d)
    with tabs[4]:
        briefing_tab(d)
    with tabs[5]:
        policy_map_tab(p, jur, incidents_all)
    with tabs[6]:
        policy_timeline_tab(p)
    with tabs[7]:
        compare_tab(p, jur, incidents_all)
    with tabs[8]:
        ask_tab(policies_all)

    st.divider()
    st.caption(
        "**Incident data:** [AI Incident Database](https://incidentdatabase.ai) (Responsible AI Collaborative, CC BY-SA 4.0), "
        "[AIAAIC Repository](https://www.aiaaic.org/aiaaic-repository) (CC BY-SA 4.0), "
        "[OECD AI Incidents Monitor](https://oecd.ai/en/incidents) and [MIT AI Risk Repository](https://airisk.mit.edu), "
        "via the [GenAI & Agentic AI Incidents](https://github.com/emmanuelgjr/genai_agentic_incidents) corpus. "
        "**Policy data:** [AI Policy Tracker](https://github.com/8h45k4r/aipolicytracker) (CC BY 4.0) and "
        "[Global AI Atlas](https://github.com/artvana/global-ai-atlas) (MIT)."
    )


if __name__ == "__main__":
    main()
