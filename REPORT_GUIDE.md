# Notes for your own report

Use this worksheet after inspecting real outputs. Write the final report yourself in your own words, as required. Do not submit this worksheet as a completed report.

## 1. Architecture comparison

- What is embedded independently in the Bi-Encoder?
- What can be computed once and reused?
- What changes when query and chunk tokens are processed jointly?
- Why are Cross-Encoder scores different from cosine similarity?

Your explanation:

## 2. Failure cases and rank shifts

For each demonstrated recovery, record:

- Exact query and why it is difficult for this document.
- Source PDF page, printed page, and section.
- Critical clause and chunk identifier.
- Original rank and re-ranked position.
- What the original three chunks establish and omit.
- Actual Answer 1/Answer 2 behavior: correct statement, omission, mistaken qualification, unsupported statement, or abstention.
- Whether answer quality improved and the supporting evidence.

Use saved candidate tables and answers. Check equivalent evidence in other baseline chunks before claiming absence. A rank improvement alone does not establish an answer improvement.

Your case notes:

## 3. Latency profiling

Use results/latency_summary.csv and results/latency_samples.csv.

- What hardware and settings were used?
- What is included in baseline, incremental re-ranking, and advanced total?
- What is excluded as setup or generation?
- What overhead do measurements show?
- How much precision can seven repetitions support?

Your observations:

## 4. Scaling

- What work must be repeated for each query if the Cross-Encoder scores every chunk?
- How does vector search limit that work?
- What happens when essential evidence is absent from the original ten candidates?

Your explanation:

## Final completeness check

- At least two genuine document-specific failure/recovery demonstrations.
- Before/after ranks and actual paired answers.
- Measured latency table with clear boundaries.
- Architecture and scaling explanations.
- Accessible GitHub link and all required code.
- Concise report in your own words.
