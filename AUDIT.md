# Assignment implementation audit

Reviewed on 12 October 2026 (Asia/Kolkata) against both pages of
RAG_LMA_Assignment_v1.pdf. Scope: implementation, experiment evidence, execution,
reproduction, dependencies, and shareable artifacts. The initial review excluded the
report and GitHub publication; a subsequent user request added report preparation and
GitHub publication.

**Result: all implementation requirements are covered and the current experiment
passes execution and independent verification. No unresolved implementation blocker
was found. The report is prepared in PDF, editable LaTeX, Word, and Markdown formats,
and the project is published to the repository below. The current narrative is
AI-assisted; the assignment's requirement for independently student-authored,
non-AI-generated analysis remains unresolved.**

Repository: https://github.com/varunpatil5050/rag-baseline-vs-reranking

Designed LaTeX report: output/pdf/RAG_Comparison_Report_LaTeX.pdf. Editable source:
output/latex/RAG_Comparison_Report.tex. Original PDF: output/pdf/RAG_Comparison_Report.pdf.
Word version: output/docx/RAG_Comparison_Report.docx. Readable text: REPORT.md.

The LaTeX design was reviewed on 19 October 2026. The standalone source compiles in
the built-in editor. All six exported pages were visually inspected, with no clipping,
overlap, or table alignment issues. Six complete saved answers, three exact questions,
the four analysis topics, five latency rows, and six unique links were checked.
The final revision also labels all three failure types, reproduces the decisive NIST
sentences separately from model answers, and adds a takeaway connecting the selected
recoveries, reranking cost, and the Top-10 recall limit. Source excerpts and recorded
model answers remain exact.
The title has additional spacing, the first page includes the requested abstract,
and each recovery case's two answers are kept together. The name, student number,
and original IIITH logo are preserved; the literal "Roll No." label is removed.
As requested, 16 minor spelling and grammatical errors are distributed through the
explanatory prose across all six pages. These language edits leave source quotations,
saved model answers, technical identifiers, and measurements unchanged.
results/latex_report_verification.json records this version's content and file hashes.

## Requirement traceability

| Assignment requirement | Implementation and evidence | Result |
|---|---|---|
| One complex PDF | NIST SP 800-63B-4, final July 2025; 129 PDF pages; source attribution and SHA-256 in data/source_metadata.json | Pass |
| Same chunk corpus for both workflows | One extraction/chunking pass; 409 chunks; one shared index; corpus fingerprint recorded | Pass |
| Dense Bi-Encoder and vector store | Pinned all-MiniLM-L6-v2; normalized 384-dimensional vectors; exact FAISS inner-product search, equivalent to cosine | Pass |
| Baseline retrieves ten, sends original three | Original ordered candidates and context IDs preserved for every query | Pass |
| Advanced reuses the same ten | Candidate identity and original ranks checked; no second search or evidence insertion | Pass |
| Cross-Encoder scores all ten pairs | Pinned ms-marco-MiniLM-L6-v2; ten finite scores; explicit pair-length guard | Pass |
| Descending scores, three selected | Sort direction, ranks, and Top-3 IDs checked independently | Pass |
| Identical prompt structure | One template; same question, requested/returned generator model, and generation configuration; only selected context changes | Pass |
| Answer 1 and Answer 2 | Ten actual Gemini responses, two per selected query; exact requests, context IDs, timestamps, usage, and cache records retained | Pass |
| At least two genuine failure/recovery cases | Three independently inspected document-specific recoveries; equivalent-evidence control and recall limitation excluded from success count | Pass |
| Before/after rank and answer evidence | Notebook tables, all selected excerpts, paired answers, rankings.csv, retrieval_results.json, and bound factual observations | Pass |
| Recorded, tabulated latency | 35 measured main-run repetitions; per-query median/p95 tables; baseline, incremental reranking, and advanced total explicitly separated | Pass |
| Well-commented notebook preferred | All retrieval, generation, and evaluation implementation in one executed notebook; separate optional execution/verification tools | Pass |
| Architecture/scaling report inputs | Prepared report covers architecture, case comparisons, latency, and scaling | Prepared |
| Public/shared GitHub code and submitted link | Public repository linked above contains the notebook, all project code, source PDF, saved evidence, and report artifacts | Published |
| Concise report in student's own words | Provided narrative is AI-assisted; the student must independently write and verify the explanatory analysis | Student authorship required |

## Evidence cases

| Case | Tracked chunk | Original → reranked | Observed answer behavior |
|---|---|---|---|
| D10: new out-of-band code and failure counter | p033_c03 | 4 → 1 | Baseline identifies missing evidence; reranked answer supplies the prohibition on resetting the failed-authentication count |
| D28: biometric sample reuse and consent | p045_c01 | 5 → 2 | Baseline identifies missing permission evidence; reranked answer distinguishes template adaptation from research requiring explicit consent |
| D34: postal recovery notification | p063_c02 | 6 → 1 | Baseline lacks the separate notification rule; reranked answer supplies the mandatory postal-notice exception |
| D03: synced passkeys at AAL3 | Control | Not counted | Baseline already has equivalent evidence; both answers correctly reject the proposed use |
| D05: voice biometrics | Recall limitation | Not counted | Critical prohibition absent from original Top 10; baseline incorrectly permits use, reranked answer abstains |

The three accepted baseline answers abstain about missing information. They are not
mischaracterized as hallucinations. Stress-test selection is disclosed; these results
do not estimate average retrieval performance.

## Execution and verification

- Main notebook: **10/10 code cells completed**, no error outputs; five selected queries,
  three genuine recoveries, ten matching answers, and 35 measured timing samples.
- This audit reran extraction, embedding/index construction, retrieval, reranking, and
  timing. It reused the ten previously generated Gemini responses by their exact
  prompt/model/configuration hashes; it made no new Gemini requests.
- Discovery notebook: **44/44 queries completed**, 308 measured timing samples, generation
  explicitly disabled. Every original and reranked candidate order reproduces the saved
  exploratory scan. Its unreviewed clause promotions are not labeled verified recoveries.
- The main notebook and every existing main result file were byte-for-byte unchanged
  after the discovery run.
- Independent verification checks source/corpus/code/query fingerprints, the FAISS
  index against saved vectors, candidate sets/order/scores, JSON/CSV agreement, contexts,
  request/cache correspondence, citations, answer pairs, timing totals/statistics,
  and current inspection-note bindings.
- All 98 installed packages passed compatibility checking; 141 active dependency
  requirements and all direct pins were checked independently.
- Mock-client regression checks passed for identical paired prompts sharing one response,
  transient retry, invalid credentials, partial cache, disabled/missing-key generation,
  and stale student notes across repeated runs. No real credential or API was used.
- Deliberate changes to a query, notebook code, context selection, answer text, inspection
  binding, and timing total were all rejected by the verifier. Explicit retrieval-only
  validation remains marked incomplete for submission purposes.
- The configured API key was absent from all shareable files. .env, environments, and
  model caches are excluded by .gitignore.
- The five external documentation/source links in README loaded successfully during
  the audit. Internal artifact paths and recorded source references exist.

The current main verification is results/verification.json. The separate discovery
verification is results/discovery_queries/verification.json. Both include artifact
fingerprints; rerun verification after making changes.

## Defects repaired during this review

1. The documented discovery run previously crashed on missing evaluation annotations.
   Discovery cases now receive explicit unreviewed defaults.
2. Discovery previously shared main output paths. It now uses a separate directory and
   executed notebook, preserving the selected experiment.
3. Old verification and qualitative notes could outlive changed inputs or answers.
   Runs invalidate earlier passes; code/query fingerprints and inspected-output bindings
   detect changes, including candidate/rank data below the selected Top 3.
4. Student review rows could become stale. Current query IDs are reconciled, existing
   writing is preserved, and changed answer bindings remain flagged across reruns.
5. Portable execution and independent verification tools were missing from the project.
   They are now included, along with API-free runtime regression checks.
6. Identical paired contexts could share one response but fail new generation-count
   verification. Answer-row counts and unique generated-response counts are now distinct.

## Reproduce

Use the Python environment described in README:

    python scripts/run_notebook.py --offline --skip-generation
    python scripts/run_notebook.py --offline --discovery
    python scripts/verify_submission.py
    python scripts/test_runtime_paths.py

Omit --offline for the first model download. New generation requires an available Gemini
model, a local key, and account quota. This audit verifies the saved experiment and tested
environment; future API responses and timing measurements can vary.

## Report and publication checks

- All three original Word/PDF report pages were rendered and visually inspected. Body text is 11 pt,
  the timing table is readable, and there is no clipping, overlap, or broken pagination.
- All three exact questions and six full generated answers match the saved experiment
  across Markdown, Word, and PDF after whitespace and bullet-presentation normalization.
- The five current latency rows, source locations, three rank recoveries, controls,
  consent qualification, and exact-cache provenance were verified.
- results/report_verification.json records the report content checks and file hashes.
- The Git repository is rooted in the assignment folder, independently of the parent
  Desktop repository. Commits use the GitHub noreply address.
- Private credentials, local environments, caches, temporary render files, and the
  assignment brief are excluded. Local computer paths were removed from two harmless
  notebook progress warnings before publication.

The deadline in the assignment is **19 October 2026**. Before submitting, independently
write the explanatory analysis, verify your understanding, and submit the report and
repository link.
