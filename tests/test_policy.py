import policy as pol


def test_policy_data_loads():
    p = pol.load_policies()
    assert len(p) > 1000
    assert {"jurisdiction", "instrument_type", "status", "binding", "topics"} <= set(p.columns)
    assert p.loc[p["short_title"] == "EU AI Act", "date"].dt.year.iloc[0] == 2024


def test_search_finds_relevant_instruments():
    idx = pol.PolicyIndex(pol.load_policies())
    hits = idx.search("deepfakes in elections", k=5)
    assert len(hits) == 5
    assert hits["title"].str.contains("deepfake|election", case=False).all()


def test_search_respects_jurisdiction_filter():
    idx = pol.PolicyIndex(pol.load_policies())
    hits = idx.search("artificial intelligence act", k=5, jurisdictions=["European Union"])
    assert (hits["jurisdiction"] == "European Union").all()


def test_incident_country_matching():
    import pandas as pd
    inc = pd.DataFrame({"jurisdiction": ["Unknown", "UK"], "title": ["Chinese firm deepfake", "Police trial"]})
    countries = set(pol.incident_countries(inc))
    assert {"China", "United Kingdom"} <= countries


def test_answer_without_key_returns_none(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    idx = pol.PolicyIndex(pol.load_policies())
    assert pol.answer("deepfakes", idx.search("deepfakes", k=3)) is None
