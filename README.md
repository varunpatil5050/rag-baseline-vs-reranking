# RAG: Baseline versus Re-Ranking

A controlled comparison over one complex PDF, implemented in a single commented notebook.

[GitHub repository](https://github.com/varunpatil5050/rag-baseline-vs-reranking)

## Report

- [LaTeX report (PDF)](output/pdf/RAG_Comparison_Report_LaTeX.pdf)
- [Editable LaTeX source](output/latex/RAG_Comparison_Report.tex)
- [Original PDF report](output/pdf/RAG_Comparison_Report.pdf)
- [Editable Word report](output/docx/RAG_Comparison_Report.docx)
- [Report text](REPORT.md)

The report covers architecture, three document-specific recovery cases with actual
answer pairs, measured latency, and scaling. It was prepared with AI assistance.
The assignment requires the student's own wording; verify and revise the editable
report before submitting it.

The LaTeX version is a standalone source with no external images or data files.
Open it in the built-in LaTeX editor for an editable source and live PDF preview,
then export the compiled PDF. Its three-page layout includes a pipeline diagram,
all six recovery-case answers, rank shifts, the latency table, and linked references.
results/latex_report_verification.json records its content checks and file hashes.

The optional Word/Markdown report builder reads the saved experiment without calling Gemini:

    python -m pip install -r requirements-report.txt
    python scripts/build_report.py

It rebuilds the Markdown and Word files, independently of the LaTeX version;
export the Word version to PDF separately.
Preserve your own revisions before rebuilding, because generated report files are overwritten.

## Files

- **RAG_Baseline_vs_Reranking.ipynb** — extraction, chunking, dense search, re-ranking, evidence, latency, and paired Gemini answers.
- **data/NIST.SP.800-63B-4.pdf** — the single source PDF.
- **data/source_metadata.json** — source, edition, page count, and SHA-256.
- **data/model_metadata.json** — pinned Hugging Face revisions.
- **data/queries.json** — selected queries and document-grounded expected evidence.
- **data/discovery_queries.json** and **results/discovery_results.json** — complete exploratory queries and observed rankings, preserving selection history.
- **results/** — candidates, selected context, timings, actual answers, and runtime metadata.
- **REPORT_GUIDE.md** — prompts for the student-authored report.
- **REPORT.md** and **output/** — report text, PDFs, and editable LaTeX and Word versions.
- **scripts/run_notebook.py** — portable execution using the selected Python environment, followed by verification.
- **scripts/verify_submission.py** — independent checks of exported artifacts, provenance, candidate/prompt controls, dependencies, and credential leakage.
- **scripts/test_runtime_paths.py** — cache, retry, partial-generation, and review-note regression checks using fake clients and temporary files.
- **scripts/build_report.py** and **requirements-report.txt** — optional report reconstruction from saved results.
- **AUDIT.md** — requirement-by-requirement readiness review; not the submission report.

## Run

Python 3.12 is recommended.

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt

If an existing environment lacks pip, run `python -m ensurepip --upgrade` first.
requirements.txt pins the direct dependencies. requirements.lock.txt records the full
tested Python 3.12/macOS environment; it is an environment snapshot, including
platform-specific packages, rather than a universal cross-platform lock.

Copy .env.example to .env if .env does not exist. Enter your own Gemini API key and a model available to your account. Never commit .env. Create a key in [Google AI Studio](https://aistudio.google.com/apikey).

Open the notebook with .venv as its Python kernel and run cells in order from the assignment folder. An editor with notebook support can use the included ipykernel package. For a separate Jupyter interface, install JupyterLab in the same environment.

Alternatively, execute and verify the notebook from this environment:

    python scripts/run_notebook.py

After the models are cached, a repeat run with no new API calls is:

    python scripts/run_notebook.py --offline --skip-generation

Matching saved Gemini responses are still reused. `--offline` applies to retrieval-model
downloads; `--skip-generation` disables new Gemini requests. To verify saved files alone:

    python scripts/verify_submission.py

To test generation control paths without using an API key or making API calls:

    python scripts/test_runtime_paths.py

The runner uses the invoking Python interpreter as the kernel, saves successful outputs,
and preserves a diagnostic notebook separately on failure. Running through an editor
performs the notebook's own checks; save it and run the independent verifier afterward.

The first run downloads the two public retrieval models. These and the environment are excluded from GitHub. The source PDF is included: its notice on PDF page 3 states that it is not subject to copyright in the United States. Retain attribution.

Generation reads the key locally and sends only the question and three selected excerpts to Gemini. Without a key, retrieval and timing can run; the notebook marks generation as pending. Cached answers are reused only for identical prompt/model/configuration hashes.

## Comparison

- Bi-Encoder: sentence-transformers/all-MiniLM-L6-v2.
- Vector store: exact FAISS inner-product search over normalized vectors (cosine similarity).
- Baseline: Top 10 retrieved, original Top 3 supplied to Gemini.
- Cross-Encoder: cross-encoder/ms-marco-MiniLM-L6-v2; all original ten pairs scored, descending scores, new Top 3 supplied to Gemini.
- Corpus: body and appendices from PDF page 12 onward; fixed 180-token chunks with 40-token overlap.
- Controls: same corpus, candidates, query, Gemini model/settings, and prompt template.

Stress queries investigate failures; their results must not be represented as an unbiased estimate of average performance. Read contexts, source passages, and both answers before making qualitative claims.

The selected evaluation contains three manually checked recoveries (D10, D28, D34), an equivalent-evidence control (D03), and a Top-10 recall limitation (D05). D03 is deliberately not counted as a failure: another baseline chunk already contains the answer despite promotion of the designated clause. The selection audit records why apparent recoveries were accepted or rejected.

## Observed results

The notebook executed successfully with ten actual Gemini answers. For the three recovery cases, baseline answers explicitly identify missing evidence; re-ranked answers supply the correct rule with supporting citations.

| Case | Tracked chunk | Baseline rank | Re-ranked rank |
|---|---|---:|---:|
| D10: new code and failed-attempt counter | p033_c03 | 4 | 1 |
| D28: biometric sample reuse and consent | p045_c01 | 5 | 2 |
| D34: postal recovery-notification exception | p063_c02 | 6 | 1 |

Both answers are correct in the D03 control. For D05, the baseline incorrectly permits voice biometrics; the re-ranked answer abstains. The actual prohibition is absent from the initial Top 10, so this case does not demonstrate recovery of the missing rule.

Per-query median and p95 retrieval timings are in results/latency_summary.csv, with all
individual samples in results/latency_samples.csv. They are measured on the development
Mac with one CPU thread; they are not universal performance figures.

Results include five queries, 35 measured retrieval repetitions, and three verified recovery cases. Candidate identities, prompt controls, source hash, citations, normalized embeddings, and absence of the configured API key from shareable files are checked by the verifier. results/verification.json records the latest check and artifact fingerprints. Each new run invalidates an earlier pass. Factual observations in results/observations.json are bound to the exact inspected requests and answer text; changed outputs require renewed inspection. The prepared report needs the student's own-word revision before submission.

To rerun all 44 discovery queries without generating Gemini answers:

    python scripts/run_notebook.py --discovery

Add `--offline` when the models are already cached. Discovery exports, timings, checks,
and its executed notebook go into results/discovery_queries/ and cannot overwrite the
selected five-case experiment. Discovery cases have an unreviewed exploratory role;
clause promotion alone is not counted as verified recovery. The original
results/discovery_results.json and discovery_metadata.json retain selection history.

results/answer_review.csv is a blank student-writing worksheet. Reruns preserve existing
writing, reconcile current query IDs, and flag notes when their answer fingerprints change.
After reviewing and revising a stale row, copy its current_answer_fingerprints value to
answer_fingerprints, then rerun the answer-display cell to mark the revised writing current.

## Measurements

Baseline latency includes query embedding, vector search, and candidate construction. Incremental re-ranking includes pair validation, tokenization, inference, sorting, and result construction. Advanced total is their sum. Each query has one warm-up and seven measured repetitions. Medians and descriptive p95 values are reported; seven samples give limited statistical precision.

Model loading, extraction/chunking, and index creation are separate setup costs. Gemini generation latency is separate. Re-running can change timings and API outputs.

CPU and FAISS use one thread consistently. This avoids an OpenMP runtime conflict observed with multithreading on the development Mac; thread settings are recorded in the results.

## Submission

The assignment requires a public or shared GitHub repository containing all code and a concise report in the student's own words. It strongly prefers one well-commented notebook. Report areas: architecture, qualitative/rank shifts, latency, and scaling. Deadline: 19 October 2026.

The published repository excludes .env, local environments, model caches, temporary
render files, and the assignment brief. Inspect the report and revise its wording to
meet the authenticity requirement before submitting the repository link and report.

## Sources

- [NIST publication](https://csrc.nist.gov/pubs/sp/800/63/b/4/final)
- [Cross-Encoder usage](https://www.sbert.net/docs/cross_encoder/usage/usage.html)
- [Bi-Encoder model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [Cross-Encoder model](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2)
- [Gemini Python API](https://ai.google.dev/gemini-api/docs/generate-content)
