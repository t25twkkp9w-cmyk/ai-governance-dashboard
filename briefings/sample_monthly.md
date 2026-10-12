# AI Risk Briefing — Monthly
**Period:** 2026-06-01 to 2026-06-30  ·  **Compared with:** 2026-05-01 to 2026-05-31  ·  **Data current through:** 2026-09-28

## Headline
- **667 incidents** logged (+7% vs prior period, 626 before).
- **115** fall in EU AI Act *unacceptable* or *high-risk* territory (+32%).
- **155** rated Critical severity; average risk score **27.5/100**.
- Most-cited companies (alleged developer/deployer): Meta (18), Anthropic (17), OpenAI (15), Google (11), Tesla (9).
- Rising fastest: Safety & Physical Harm (+11), Surveillance & Rights (+11), Military & Geopolitical (+9).

## EU AI Act risk tiers
| Tier | Now | Prior | Change |
|---|---|---|---|
| Minimal | 316 | 284 | +11% |
| Limited / transparency (Art. 50) | 128 | 150 | -15% |
| High-risk (Annex I/III) | 113 | 86 | +31% |
| Out of scope (military, Art. 2(3)) | 66 | 57 | +16% |
| GPAI obligations (Ch. V) | 42 | 48 | -12% |
| Unacceptable (Art. 5) | 2 | 1 | +100% |

## Harm types
| Harm type | Now | Prior | Change |
|---|---|---|---|
| Other | 193 | 148 | +30% |
| Deepfakes & Misinformation | 126 | 129 | -2% |
| Security & Malicious Use | 89 | 118 | -25% |
| Military & Geopolitical | 66 | 57 | +16% |
| Surveillance & Rights | 40 | 29 | +38% |
| Safety & Physical Harm | 35 | 24 | +46% |

## NIST AI RMF
**Trustworthiness characteristic at stake**

| Characteristic | Now | Prior | Change |
|---|---|---|---|
| Valid & Reliable | 212 | 164 | +29% |
| Accountable & Transparent | 182 | 182 | +0% |
| Safe | 109 | 93 | +17% |
| Secure & Resilient | 89 | 118 | -25% |
| Privacy-Enhanced | 67 | 64 | +5% |
| Fair – Harmful Bias Managed | 8 | 5 | +60% |

**Core function most implicated**

| Function | Now | Prior | Change |
|---|---|---|---|
| MEASURE | 267 | 250 | +7% |
| MAP | 135 | 131 | +3% |
| MANAGE | 134 | 109 | +23% |
| GOVERN | 131 | 136 | -4% |

## ISO/IEC 42001 Annex A controls implicated
| Control | Objective | Incidents | Prior |
|---|---|---|---|
| A.6.2.6 | AI system operation and monitoring | 309 | 294 |
| A.5.2 | AI system impact assessment process | 297 | 223 |
| A.5.5 | Assessing societal impacts | 233 | 228 |
| A.9.4 | Intended use of the AI system | 200 | 198 |
| A.8.2 | System documentation and information for users | 168 | 168 |
| A.6.2.4 | AI system verification and validation | 151 | 163 |

## Highest-risk incidents
- **Tesla Begins Testing Fully Autonomous Cybercab Robotaxi in Austin** — 2026-06-30, Critical, risk 80 ([source](https://oecd.ai/en/incidents/2026-06-30-6404))
  - Alleged responsible party: Tesla
  - EU AI Act: High-risk (Annex I/III) · Annex I vehicles & machinery
  - NIST: Secure & Resilient (MEASURE) · ISO 42001: A.6.2.6 AI system operation and monitoring
- **Tesla Settles Lawsuit Over Fatal Full Self-Driving Crash in Arizona** — 2026-06-27, Critical, risk 80 ([source](https://oecd.ai/en/incidents/2026-06-27-4ef1))
  - Alleged responsible party: Tesla
  - EU AI Act: High-risk (Annex I/III) · Annex I vehicles & machinery
  - NIST: Safe (MANAGE) · ISO 42001: A.6.2.4 AI system verification and validation
- **AI-Powered Surveillance Breaches Lead to Security Risks and Assassinations** — 2026-06-08, Critical, risk 80 ([source](https://oecd.ai/en/incidents/2026-06-08-656a))
  - EU AI Act: High-risk (Annex I/III) · Annex III(6) law enforcement
  - NIST: Privacy-Enhanced (MEASURE) · ISO 42001: A.5.4 Assessing impact on individuals or groups
- **AI Drug Monitoring System Fails to Detect Nurse's Fentanyl Theft in Tennessee Hospital** — 2026-06-01, Critical, risk 80 ([source](https://oecd.ai/en/incidents/2026-06-01-7f83))
  - EU AI Act: High-risk (Annex I/III) · Annex I medical devices
  - NIST: Valid & Reliable (MEASURE) · ISO 42001: A.6.2.4 AI system verification and validation
- **Purportedly AI-Generated Facebook Poster Falsely Declared Kannada Actor Doddanna Dead** — 2026-06-12, Critical, risk 80 ([source](https://incidentdatabase.ai/cite/1550/))
  - EU AI Act: High-risk (Annex I/III) · Annex III(6) law enforcement
  - NIST: Safe (MANAGE) · ISO 42001: A.6.2.4 AI system verification and validation

## Recommended actions
1. **A.6.2.6 AI system operation and monitoring:** Tighten runtime monitoring and alerting for abuse, drift and anomalous outputs.
1. **A.5.2 AI system impact assessment process:** Run or refresh AI impact assessments for systems in the affected domains.
1. **A.5.5 Assessing societal impacts:** Assess societal and misuse impacts, including content provenance and abuse scenarios.

---
*Classifications are indicative keyword-rule mappings for triage, not legal determinations. Data: AI Incident Database (incidentdatabase.ai), AIAAIC Repository, OECD AI Incidents Monitor and MIT AI Risk Repository, via the GenAI & Agentic AI Incidents corpus.*

