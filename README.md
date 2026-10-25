# EvidenceXI Football 

**AI-Powered Football Tactical Evidence Analysis**

evidenceXI Football is a football analytics project designed to evaluate tactical claims against match-event data. It aims to help analysts investigate football performance through measurable questions, supporting evidence, contradictory evidence, sample sizes, and transparent limitations.

## 🎯 Problem Statement

Football teams and sports organizations use match data to evaluate performance and make tactical decisions. However, determining whether a tactical observation is consistently supported by match evidence can be challenging.

## 💡 Proposed Solution

evidenceXI Football aims to turn tactical observations into structured, evidence-based analyses. Rather than presenting statistics alone, the platform is designed to connect a tactical claim with measurable indicators and a transparent assessment of the available data.

### Key Features

- **Tactical Claim Analysis:** Translate selected football claims into measurable questions.
- **Match-Event Data Processing:** Process supported football event data for statistical analysis.
- **Evidence-Based Results:** Present relevant metrics and observations supporting or contradicting a claim.
- **Sample-Size Awareness:** Show how much data is available for an analysis.
- **Transparent Limitations:** Identify missing context and avoid overstating conclusions.
- **AI-Assisted Explanations:** Planned or optional natural-language explanations grounded in calculated results.

> Feature availability depends on the current implementation. Planned features are not necessarily available in the current version.

## 🧠 Domain

- Football and Sports Analytics
- Data Analysis and Statistical Reasoning
- Machine Learning (if implemented)
- LLM / Generative AI (if implemented)

## 🛠️ Technology Stack

The intended stack includes:

- **Frontend:** React, Vite, Tailwind CSS
- **Backend:** Python, FastAPI
- **Data Processing:** Pandas
- **Data Validation:** Pydantic
- **Visualizations:** Recharts or a comparable charting library
- **Data Source:** StatsBomb Open Data

Update this list to reflect the technologies actually used in the repository.

## ⚽ Example Use Case

**Tactical claim:** "Our right flank is vulnerable after switches of play."

A possible analysis could examine defined switch-of-play events and subsequent attacking outcomes, compare the results with an appropriate baseline, and report the number of relevant sequences alongside the limitations of the available data.

Event data alone cannot establish defensive shape, individual player responsibility, or causality.

## 📊 Data Sources

- [StatsBomb Open Data](https://github.com/statsbomb/open-data)
- [Metrica Sports Sample Data](https://github.com/metrica-sports/sample-data)
- [Wyscout Soccer Match Event Dataset](https://figshare.com/collections/Soccer_match_event_dataset/4415000)

Use datasets in accordance with their respective licenses, terms, and attribution requirements. Do not commit restricted, private, or unnecessarily large datasets to the repository.

## 🚀 Getting Started

Installation and execution instructions will be added for the current frontend and backend implementation.

Once the application structure is finalized, this section should document prerequisites, installation commands, environment variables, and how to run the application locally.

## 🔬 Project Approach

1. Load and validate supported match-event data.
2. Define a tactical claim and its measurable indicators.
3. Calculate relevant metrics from the available events.
4. Compare supporting and contradictory evidence where possible.
5. Report sample size, uncertainty, and data limitations.
6. Present a cautious conclusion based on the analysis.

## ⚠️ Limitations

- Results depend on the quality and coverage of the input data.
- Event data may not capture all relevant tactical context.
- Small samples can produce misleading conclusions.
- Statistical association does not establish causation.
- AI-generated explanations, if used, must be grounded in computed results and should not invent statistics.

## 🗺️ Roadmap

- [ ] Build a working match-data ingestion pipeline
- [ ] Implement a reproducible tactical-claim analysis
- [ ] Display supporting and contradictory evidence
- [ ] Add sample sizes and limitations to reports
- [ ] Improve visualizations and user experience
- [ ] Add optional AI-assisted explanations
- [ ] Deploy the application

## 🤝 Contributions

Contributions, feedback, and ideas for improving transparent football analysis are welcome.

## 📄 License

Add a license once the project's licensing terms have been selected and verified.

---

**evidenceXI Football**  
*Turning football claims into testable questions and transparent evidence.*
