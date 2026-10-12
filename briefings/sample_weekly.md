# AI Risk Briefing — Weekly
**Period:** 2026-07-06 to 2026-07-12  ·  **Compared with:** 2026-06-29 to 2026-07-05  ·  **Data current through:** 2026-09-28

## Headline
- **133 incidents** logged (+28% vs prior period, 104 before).
- **22** fall in EU AI Act *unacceptable* or *high-risk* territory (+100%).
- **30** rated Critical severity; average risk score **27.9/100**.
- Most-cited companies (alleged developer/deployer): Meta (10), OpenAI (5), Anthropic (3), Tesla (3), US Military (1).
- Rising fastest: Deepfakes & Misinformation (+6), Reliability & Hallucination (+6), Privacy & Data Protection (+5).

## EU AI Act risk tiers
| Tier | Now | Prior | Change |
|---|---|---|---|
| Minimal | 66 | 54 | +22% |
| Limited / transparency (Art. 50) | 28 | 24 | +17% |
| High-risk (Annex I/III) | 22 | 11 | +100% |
| Out of scope (military, Art. 2(3)) | 9 | 9 | +0% |
| GPAI obligations (Ch. V) | 8 | 6 | +33% |

## Harm types
| Harm type | Now | Prior | Change |
|---|---|---|---|
| Other | 31 | 22 | +41% |
| Deepfakes & Misinformation | 27 | 21 | +29% |
| Security & Malicious Use | 17 | 18 | -6% |
| Privacy & Data Protection | 11 | 6 | +83% |
| Military & Geopolitical | 9 | 9 | +0% |
| Reliability & Hallucination | 9 | 3 | +200% |

## NIST AI RMF
**Trustworthiness characteristic at stake**

| Characteristic | Now | Prior | Change |
|---|---|---|---|
| Valid & Reliable | 40 | 25 | +60% |
| Accountable & Transparent | 38 | 32 | +19% |
| Safe | 19 | 20 | -5% |
| Privacy-Enhanced | 18 | 8 | +125% |
| Secure & Resilient | 17 | 18 | -6% |
| Fair – Harmful Bias Managed | 1 | 1 | +0% |

**Core function most implicated**

| Function | Now | Prior | Change |
|---|---|---|---|
| MEASURE | 74 | 48 | +54% |
| MAP | 24 | 21 | +14% |
| GOVERN | 19 | 18 | +6% |
| MANAGE | 16 | 17 | -6% |

## ISO/IEC 42001 Annex A controls implicated
| Control | Objective | Incidents | Prior |
|---|---|---|---|
| A.6.2.6 | AI system operation and monitoring | 58 | 46 |
| A.5.2 | AI system impact assessment process | 57 | 37 |
| A.5.5 | Assessing societal impacts | 43 | 39 |
| A.8.2 | System documentation and information for users | 41 | 29 |
| A.9.4 | Intended use of the AI system | 37 | 33 |
| A.6.2.4 | AI system verification and validation | 36 | 30 |

## Highest-risk incidents
- **Tesla Autopilot Fails to Detect Sleeping Driver, Endangering Children in Canada** — 2026-07-06, Critical, risk 80 ([source](https://oecd.ai/en/incidents/2026-07-06-1501))
  - Alleged responsible party: Tesla
  - EU AI Act: High-risk (Annex I/III) · Annex I vehicles & machinery
  - NIST: Valid & Reliable (MEASURE) · ISO 42001: A.6.2.4 AI system verification and validation
- **US Regulators Warn Self-Driving Car Companies Over Interference with Emergency Responders** — 2026-07-08, Critical, risk 80 ([source](https://oecd.ai/en/incidents/2026-07-08-b586))
  - EU AI Act: High-risk (Annex I/III) · Annex I vehicles & machinery
  - NIST: Accountable & Transparent (MEASURE) · ISO 42001: A.2.2 AI policy
- **Madison Square Garden's AI Surveillance System Secretly Profiles and Scores Celebrities** — 2026-07-09, High, risk 60 ([source](https://oecd.ai/en/incidents/2026-07-09-1f2b))
  - EU AI Act: High-risk (Annex I/III) · Annex III(6) law enforcement
  - NIST: Privacy-Enhanced (GOVERN) · ISO 42001: A.5.4 Assessing impact on individuals or groups
- **Tesla Launches Unsupervised Robotaxi in Miami Amid Safety Concerns** — 2026-07-09, High, risk 60 ([source](https://oecd.ai/en/incidents/2026-07-09-407b))
  - Alleged responsible party: Tesla
  - EU AI Act: High-risk (Annex I/III) · Annex I vehicles & machinery
  - NIST: Safe (MEASURE) · ISO 42001: A.6.2.4 AI system verification and validation
- **Transnational AI-Driven Visa Fraud Network Dismantled in Colombia** — 2026-07-12, High, risk 60 ([source](https://oecd.ai/en/incidents/2026-07-12-b017))
  - EU AI Act: High-risk (Annex I/III) · Annex III(7) migration & border
  - NIST: Accountable & Transparent (MAP) · ISO 42001: A.9.4 Intended use of the AI system

## Recommended actions
1. **A.6.2.6 AI system operation and monitoring:** Tighten runtime monitoring and alerting for abuse, drift and anomalous outputs.
1. **A.5.2 AI system impact assessment process:** Run or refresh AI impact assessments for systems in the affected domains.
1. **A.5.5 Assessing societal impacts:** Assess societal and misuse impacts, including content provenance and abuse scenarios.

---
*Classifications are indicative keyword-rule mappings for triage, not legal determinations. Data: AI Incident Database (incidentdatabase.ai), AIAAIC Repository, OECD AI Incidents Monitor and MIT AI Risk Repository, via the GenAI & Agentic AI Incidents corpus.*

