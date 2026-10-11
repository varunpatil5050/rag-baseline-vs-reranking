"""Verify the current executed experiment without generating new API responses.

Run from the project's Python environment. The checks validate recorded evidence and
controls; they do not replace reading the source passages or judging answer quality.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
from datetime import datetime, timezone

for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[variable] = "1"

import nbformat
import numpy as np
import pandas as pd
import faiss
from dotenv import dotenv_values
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def normalize(value: str) -> str:
    import unicodedata
    return " ".join(unicodedata.normalize("NFKC", value).split()).casefold()


def verify(results_dir: Path, allow_incomplete_answers: bool = False) -> dict:
    faiss.omp_set_num_threads(1)
    runtime = read_json(results_dir / "run_metadata.json")
    query_path = ROOT / runtime["query_file"]
    query_cases = read_json(query_path)
    query_ids = [c["id"] for c in query_cases]
    assert len(query_ids) == len(set(query_ids)) >= 2, "Invalid query IDs."
    assert sha(query_path.read_bytes()) == runtime["query_file_sha256"], "Query file changed after execution."
    assert results_dir.resolve() == (ROOT / runtime["results_directory"]).resolve()
    notebook_path = (ROOT / "RAG_Baseline_vs_Reranking.ipynb" if runtime["evaluation_mode"] == "selected"
                     else results_dir / "discovery_execution.ipynb")
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)
    code_cells = [c for c in notebook.cells if c.cell_type == "code"]
    code = "\n\n".join(c.source for c in code_cells)
    assert sha(code.encode()) == runtime["notebook_code_sha256"], "Notebook code changed after execution."
    assert [c.execution_count for c in code_cells] == list(range(1, len(code_cells) + 1))
    assert not [o for c in code_cells for o in c.outputs if o.output_type == "error"]
    assert runtime["torch_threads"] == runtime["faiss_threads"] == 1
    assert runtime["top_k"] == 10 and runtime["context_k"] == 3
    assert runtime["query_count"] == len(query_ids)
    source = read_json(ROOT / "data/source_metadata.json")
    assert source == runtime["source"]
    assert sha((ROOT / "data/NIST.SP.800-63B-4.pdf").read_bytes()) == source["sha256"]
    assert len(list((ROOT / "data").glob("*.pdf"))) == 1
    assert read_json(ROOT / "data/model_metadata.json") == runtime["retrieval_models"]

    # Check active dependencies directly; the environment need not contain pip.
    active_requirements = 0
    for dist in importlib.metadata.distributions():
        for dependency in dist.requires or []:
            requirement = Requirement(dependency)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            version = importlib.metadata.version(requirement.name)
            assert requirement.specifier.contains(version, prereleases=True), f"Dependency mismatch: {requirement.name}"
            active_requirements += 1
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            requirement = Requirement(line)
            assert requirement.specifier.contains(importlib.metadata.version(requirement.name))

    chunks = read_json(results_dir / "chunks.json")
    by_id = {c["chunk_id"]: c for c in chunks}
    assert len(chunks) == len(by_id) == runtime["chunk_count"]
    assert sha(json.dumps(chunks, sort_keys=True).encode()) == runtime["corpus_sha256"]
    vectors = np.load(results_dir / "embeddings.npy")
    assert vectors.shape == (len(chunks), 384) and np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5)
    index = faiss.read_index(str(results_dir / "index.faiss"))
    assert index.ntotal == len(chunks) and index.d == vectors.shape[1]
    assert index.metric_type == faiss.METRIC_INNER_PRODUCT
    assert np.array_equal(index.reconstruct_n(0, index.ntotal), vectors)

    results = read_json(results_dir / "retrieval_results.json")
    assert [r["case"]["id"] for r in results] == query_ids, "Stale or reordered retrieval results."
    recoveries, expected_rank_rows, expected_summary_rows = [], [], []
    for case, result in zip(query_cases, results):
        assert all(result["case"].get(k) == v for k, v in case.items())
        original, ranked = result["baseline_top10"], result["reranked_top10"]
        ids = {c["chunk_id"] for c in original}
        assert len(original) == len(ranked) == len(ids) == 10
        assert ids == {c["chunk_id"] for c in ranked}
        assert [c["baseline_rank"] for c in original] == list(range(1, 11))
        assert [c["reranked_rank"] for c in ranked] == list(range(1, 11))
        assert all(original[i]["bi_score"] >= original[i+1]["bi_score"] for i in range(9))
        assert all(ranked[i]["cross_score"] >= ranked[i+1]["cross_score"] for i in range(9))
        original_by_id = {c["chunk_id"]: c for c in original}
        for chunk in original + ranked:
            assert all(chunk[k] == v for k, v in by_id[chunk["chunk_id"]].items())
            assert chunk["baseline_rank"] == original_by_id[chunk["chunk_id"]]["baseline_rank"]
            assert chunk["bi_score"] == original_by_id[chunk["chunk_id"]]["bi_score"]
            assert np.isfinite(chunk["bi_score"])
        assert all(np.isfinite(c["cross_score"]) for c in ranked)
        assert result["baseline_top3_ids"] == [c["chunk_id"] for c in original[:3]]
        assert result["reranked_top3_ids"] == [c["chunk_id"] for c in ranked[:3]]
        evidence = {c["chunk_id"] for c in chunks if c["pdf_page"] == case["source_pdf_page"]
                    and normalize(case["critical_clause"]) in normalize(c["text"])}
        assert evidence and sorted(evidence) == result["designated_evidence_ids"]
        tracked = next((c for c in ranked if c["chunk_id"] in evidence), None)
        before = tracked["baseline_rank"] if tracked else None
        after = tracked["reranked_rank"] if tracked else None
        best_original = min((c["baseline_rank"] for c in original if c["chunk_id"] in evidence), default=None)
        recovered = best_original is not None and best_original > 3 and after <= 3
        assert result["tracked_evidence_chunk_id"] == (tracked["chunk_id"] if tracked else None)
        assert (result["evidence_baseline_rank"], result["evidence_reranked_rank"]) == (before, after)
        assert result["best_original_evidence_rank"] == best_original
        assert result["designated_clause_recovered"] == recovered
        role = result["case"]["evaluation_role"]
        if role == "top10_recall_limitation":
            assert best_original is None, "Recall-limitation evidence is now present in Top 10."
        verified = recovered and role == "failure_recovery"
        if role == "failure_recovery":
            assert verified, f"Declared recovery failed: {case['id']}"
            recoveries.append(case["id"])
        for c in ranked:
            expected_rank_rows.append({"query_id": case["id"], **c,
                                       "designated_evidence": c["chunk_id"] in evidence,
                                       "in_baseline_top3": c["baseline_rank"] <= 3,
                                       "in_reranked_top3": c["reranked_rank"] <= 3})
        expected_summary_rows.append({"query_id": case["id"], "role": role, "category": case["category"],
                                      "tracked_chunk_id": tracked["chunk_id"] if tracked else None,
                                      "evidence_before": before, "evidence_after": after,
                                      "clause_recovered": recovered, "verified_failure_recovery": verified,
                                      "query": case["query"]})
    if runtime["evaluation_mode"] == "selected":
        assert len(recoveries) >= 2
    pd.testing.assert_frame_equal(pd.read_csv(results_dir / "rankings.csv", dtype={"printed_page": str}), pd.DataFrame(expected_rank_rows),
                                  check_dtype=False, check_exact=False)
    pd.testing.assert_frame_equal(pd.read_csv(results_dir / "query_summary.csv"), pd.DataFrame(expected_summary_rows),
                                  check_dtype=False, check_exact=False)

    literal_assignments = {}
    for cell in code_cells:
        for node in ast.walk(ast.parse(cell.source)):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {"PROMPT_TEMPLATE", "generation_config"}:
                        literal_assignments[target.id] = ast.literal_eval(node.value)
    answers = read_json(results_dir / "answers.json")
    answer_cache = read_json(results_dir / "answer_cache.json") if (results_dir / "answer_cache.json").exists() else {}
    if not allow_incomplete_answers:
        assert runtime["answer_status"] == "complete"
        assert len(answers) == 2 * len(query_ids)
    assert runtime["paired_answers_present"] == len(answers)
    assert len({(a["query_id"], a["variant"]) for a in answers}) == len(answers)
    assert runtime["answers_reused_from_exact_request_cache"] + runtime["answers_generated_this_run"] == len(answers)
    answer_checks = []
    for answer in answers:
        result = next(r for r in results if r["case"]["id"] == answer["query_id"])
        assert answer["variant"] in {"baseline", "reranked"}
        ids = result[answer["variant"] + "_top3_ids"]
        assert answer["context_ids"] == ids
        context = "\n\n".join(f"[{c['chunk_id']}; PDF page {c['pdf_page']}; printed page {c['printed_page']}]\n{c['text']}"
                                for c in [by_id[cid] for cid in ids])
        assert answer["prompt"] == literal_assignments["PROMPT_TEMPLATE"].format(question=result["case"]["query"], context=context)
        assert answer["generation_config"] == literal_assignments["generation_config"]
        assert answer["model_requested"] == runtime["gemini_model_requested"]
        payload = {"model": answer["model_requested"], "config": answer["generation_config"], "prompt": answer["prompt"]}
        assert sha(json.dumps(payload, sort_keys=True).encode()) == answer["request_sha256"]
        cached = answer_cache[answer["request_sha256"]]
        assert all(answer[k] == v for k, v in cached.items())
        citations = set(re.findall(r"\bp\d{3}_c\d{2}\b", answer["answer"]))
        assert citations and citations <= set(ids), "Invalid or missing chunk citation."
        assert answer["answer"].strip() and len(answer["answer"].split()) <= 150
        assert answer["generation_ms"] > 0 and answer.get("attempts", 1) in {1, 2}
        assert answer["model_returned"] and answer["generated_utc"]
        answer_checks.append({"query_id": answer["query_id"], "variant": answer["variant"],
                              "words": len(answer["answer"].split()), "citations_in_context": True})
    if not allow_incomplete_answers:
        assert {(a["query_id"], a["variant"]) for a in answers} == {
            (qid, variant) for qid in query_ids for variant in ("baseline", "reranked")}
        assert len({a["model_returned"] for a in answers}) == 1, "Returned model versions differ."

    timings = pd.read_csv(results_dir / "latency_samples.csv")
    assert set(timings.query_id) == set(query_ids)
    repetitions = runtime["latency_repetitions"]
    for _, rows in timings.groupby("query_id"):
        assert sorted(rows.repetition.tolist()) == list(range(1, repetitions + 1))
    assert np.allclose(timings.baseline_ms + timings.rerank_increment_ms, timings.advanced_total_ms)
    assert (timings[["baseline_ms", "rerank_increment_ms", "advanced_total_ms"]] > 0).all().all()
    expected_latency = timings.groupby("query_id").agg(
        baseline_median_ms=("baseline_ms", "median"),
        rerank_increment_median_ms=("rerank_increment_ms", "median"),
        advanced_total_median_ms=("advanced_total_ms", "median"),
        baseline_p95_ms=("baseline_ms", lambda x: np.percentile(x, 95)),
        advanced_total_p95_ms=("advanced_total_ms", lambda x: np.percentile(x, 95)))
    expected_latency["advanced_over_baseline"] = expected_latency.advanced_total_median_ms / expected_latency.baseline_median_ms
    pd.testing.assert_frame_equal(pd.read_csv(results_dir / "latency_summary.csv", index_col="query_id"),
                                  expected_latency, check_exact=False)
    review = pd.read_csv(results_dir / "answer_review.csv")
    assert review.query_id.tolist() == query_ids
    checks = read_json(results_dir / "notebook_checks.json")
    assert checks["query_file_sha256"] == runtime["query_file_sha256"]
    assert checks["notebook_code_sha256"] == runtime["notebook_code_sha256"]
    assert checks["matching_answers"] == len(answers) and checks["expected_answers"] == 2 * len(query_ids)
    assert checks["verified_retrieval_recoveries"] == recoveries
    for row in review.to_dict("records"):
        binding = {a["variant"]: {"request_sha256": a["request_sha256"], "answer_sha256": sha(a["answer"].encode())}
                   for a in answers if a["query_id"] == row["query_id"]}
        assert json.loads(row["current_answer_fingerprints"]) == binding
        notes = [row.get(column) for column in ("baseline_observation", "reranked_observation",
                 "supporting_chunk_ids", "improvement_demonstrated", "student_explanation")]
        has_notes = any(pd.notna(value) and str(value) for value in notes)
        expected_status = ("blank" if not has_notes else "current" if
                           json.loads(row["answer_fingerprints"]) == binding else "stale_preserved")
        assert row["review_status"] == expected_status

    # Static human-inspection notes belong to the selected experiment only.
    complete_answers = runtime["answer_status"] == "complete" and len(answers) == 2 * len(query_ids)
    if runtime["evaluation_mode"] == "selected" and complete_answers:
        selection = read_json(results_dir / "selection_audit.json")
        assert selection["accepted_failure_recovery_ids"] == recoveries
        observations = read_json(results_dir / "observations.json")["observations"]
        assert checks["inspection_notes_match_current_outputs"], "Qualitative observations need renewed inspection."
        expected_binding = {"source_sha256": source["sha256"], "corpus_sha256": runtime["corpus_sha256"],
                            "query_file_sha256": runtime["query_file_sha256"], "retrieval_models": runtime["retrieval_models"],
                            "retrieval_evidence_sha256": sha(json.dumps([
                                {"query_id": r["case"]["id"], "baseline": r["baseline_top10"],
                                 "reranked": r["reranked_top10"]} for r in results], sort_keys=True).encode()),
                            "answer_fingerprints": {a["query_id"] + "/" + a["variant"]: {
                                "request_sha256": a["request_sha256"], "answer_sha256": sha(a["answer"].encode())} for a in answers}}
        assert read_json(results_dir / "observations.json")["inspected_output_fingerprints"] == expected_binding
        assert [o["query_id"] for o in observations] == query_ids
        for observation in observations:
            result = next(r for r in results if r["case"]["id"] == observation["query_id"])
            if "tracked_chunk" in observation:
                assert observation["tracked_chunk"] == result["tracked_evidence_chunk_id"]
                assert (observation["rank_before"], observation["rank_after"]) == (
                    result["evidence_baseline_rank"], result["evidence_reranked_rank"])

    key = dotenv_values(ROOT / ".env").get("GEMINI_API_KEY", "")
    shareable = [p for p in ROOT.rglob("*") if p.is_file() and p.name != ".env"
                 and not any(part in {".venv", ".cache", ".git", "__pycache__", ".ipynb_checkpoints"}
                             for part in p.relative_to(ROOT).parts)]
    if key:
        assert not any(key.encode() in p.read_bytes() for p in shareable), "Credential found in shareable file."
    fingerprints = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
                    [notebook_path, query_path, ROOT / "data/model_metadata.json", ROOT / "data/source_metadata.json"]}
    fingerprints.update({str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
                         [ROOT / "requirements.txt", ROOT / "requirements.lock.txt", ROOT / "requirements-report.txt",
                          *sorted((ROOT / "scripts").glob("*.py"))]})
    fingerprints.update({str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in results_dir.iterdir()
                         if p.is_file() and p.name != "verification.json" and not p.name.startswith(".")})
    return {"status": "passed", "verified_utc": datetime.now(timezone.utc).isoformat(),
            "evaluation_mode": runtime["evaluation_mode"], "executed_notebook_code_cells": len(code_cells),
            "source_hash_verified": True, "chunks": len(chunks), "queries": len(query_ids),
            "verified_retrieval_recoveries": recoveries, "gemini_answers": len(answers),
            "answers_reused_from_exact_request_cache": runtime["answers_reused_from_exact_request_cache"],
            "submission_experiment_complete": runtime["evaluation_mode"] == "selected" and complete_answers,
            "inspection_notes_match_current_outputs": checks["inspection_notes_match_current_outputs"],
            "candidate_and_prompt_controls_verified": True, "timing_samples": len(timings),
            "active_package_requirements_checked": active_requirements,
            "credential_scan": "No configured credential found in shareable files." if key else "No local credential configured; scan skipped.",
            "answer_checks": answer_checks, "artifact_sha256": fingerprints,
            "scope": "Structural and provenance checks; semantic answer judgments require source inspection."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=ROOT / "results")
    parser.add_argument("--allow-incomplete-answers", action="store_true")
    arguments = parser.parse_args()
    directory = arguments.results.resolve()
    try:
        verification = verify(directory, arguments.allow_incomplete_answers)
    except Exception as error:
        (directory / "verification.json").write_text(json.dumps({"status": "failed", "error_type": type(error).__name__,
                                                                  "verified_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n")
        raise
    (directory / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    print(f"PASS: {verification['queries']} queries; {verification['verified_retrieval_recoveries']} recoveries; "
          f"{verification['gemini_answers']} answers; {verification['timing_samples']} timing samples.")
