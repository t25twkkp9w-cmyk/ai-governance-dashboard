import pandas as pd

import briefing as br
import classify as c


def tier(text, harm=None):
    harm = harm or c.classify_harm(text, "other")
    return c.classify_eu(text, harm, [])[0]


def test_clearview_is_unacceptable():
    assert tier("Clearview AI scraped billions of facial images") == "Unacceptable (Art. 5)"


def test_hiring_is_high_risk():
    assert tier("Amazon AI hiring tool penalised women candidates") == "High-risk (Annex I/III)"


def test_deepfake_is_transparency_not_education():
    assert tier("Students share deepfake nudes of classmates at school") == "Limited / transparency (Art. 50)"


def test_military_out_of_scope():
    assert tier("Army tests AI-enabled loitering munitions") == "Out of scope (military, Art. 2(3))"


def test_word_boundaries():
    # 'rce' inside 'force' and 'hack' inside 'shack' must not trigger security
    assert c.classify_harm("Police force tests a new shack design", "other") != "Security & Malicious Use"


def test_quarter_window():
    start, end = br.period_window("quarterly", "2026-05-15")
    assert (start.date().isoformat(), end.date().isoformat()) == ("2026-04-01", "2026-06-30")


def test_week_starts_monday():
    start, end = br.period_window("weekly", "2026-07-16")  # Thursday
    assert start.weekday() == 0 and (end - start).days == 6


def test_briefing_renders():
    df = br.load("data/incidents_classified.csv")
    for p in br.PERIODS:
        md, stats = br.generate(df, p)
        assert md.startswith("# AI Risk Briefing")
        assert stats["total"] >= 0


# --- companies ---------------------------------------------------------------
import companies as co


def test_product_rolls_up_to_company():
    assert co.responsible_party("", "ChatGPT gives dangerous medical advice")[0] == "OpenAI"
    assert co.responsible_party("Instagram", "x")[0] == "Meta"


def test_first_named_company_wins_in_title():
    assert co.responsible_party("", "TikTok collected Android data in violation of Google policies")[0] == "TikTok / ByteDance"


def test_private_individuals_not_named():
    company, _, kind, _ = co.responsible_party("Michael Smith", "AI music streaming fraud")
    assert company == "" and kind == "Individual"


def test_government_detected():
    assert co.responsible_party("", "US Military forms AI task force")[2] == "Government / public body"


def test_victims_are_not_responsible():
    assert co.responsible_party("Women whose images were processed", "Nudify app")[0] == ""


# --- AI Incident Database snapshot ---------------------------------------------
import aiid


def test_aiid_entities():
    assert aiid.classify_entity("openai") == ("OpenAI", "Company")
    assert aiid.classify_entity("scammers")[1] == "Unidentified / malicious actors"
    assert aiid.classify_entity("reddit-users")[1] == "Unidentified / malicious actors"
    assert aiid.classify_entity("donald-trump") == ("", "Individual")


def test_aiid_deployer_before_developer():
    assert aiid.responsible(["tesla"], ["mobileye"])[0] == "Tesla"
    assert aiid.responsible(["scammers"], ["elevenlabs"])[0] == "ElevenLabs"


def test_classified_data_has_aiid_fields():
    df = br.load("data/incidents_classified.csv")
    a = df[df["source"] == "AIID"]
    assert len(a) > 1600
    assert (a["description"].str.len() > 50).mean() > 0.95
    assert {"alleged_deployer", "alleged_developer", "harmed_parties", "mit_risk_domain"} <= set(df.columns)


def test_cross_source_duplicates_merged():
    df = br.load("data/incidents_classified.csv")
    import pandas as pd
    m = pd.read_csv("data/raw/aiid/cross_source_matches.csv")
    assert df["id"].is_unique
    assert not df["id"].isin(m["duplicate_id"]).any()
    m2 = pd.read_csv("data/raw/aiaaic_oecd_matches.csv")
    assert not df["id"].isin(m2["duplicate_id"]).any()
    assert (df["also_reported_by"] != "").sum() == len(m) + len(m2)
