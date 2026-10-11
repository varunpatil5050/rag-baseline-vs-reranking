#!/usr/bin/env python3
"""Test notebook generation/cache/review paths without an API or real credential."""

from __future__ import annotations

from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
from unittest.mock import patch

import nbformat
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FAKE_CREDENTIAL = "fake-test-credential"


class FakeAPIError(Exception):
    def __init__(self, code: int):
        self.code = code


class FakeModels:
    def __init__(self, errors):
        self.errors = list(errors)
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return types.SimpleNamespace(
            text="Test answer [test_1].", model_version="fake-test-model",
            candidates=[types.SimpleNamespace(finish_reason="STOP")],
            usage_metadata=None,
        )


class FakeClient:
    def __init__(self, errors):
        self.models = FakeModels(errors)
        self.closed = False

    def close(self):
        self.closed = True


def execute_cell(source: str, namespace: dict) -> None:
    # Keep routine cell messages quiet; failed assertions still raise normally.
    with redirect_stdout(io.StringIO()):
        exec(compile(source, "<notebook-runtime-regression>", "exec"), namespace)


def main() -> int:
    notebook = nbformat.read(ROOT / "RAG_Baseline_vs_Reranking.ipynb", as_version=4)
    generation_cells = [
        cell.source for cell in notebook.cells
        if cell.cell_type == "code" and "PROMPT_TEMPLATE =" in cell.source
    ]
    worksheet_cells = [
        cell.source for cell in notebook.cells
        if cell.cell_type == "code" and "review_path =" in cell.source
    ]
    assert len(generation_cells) == len(worksheet_cells) == 1
    generation, worksheet = generation_cells[0], worksheet_cells[0]

    fake_google = types.ModuleType("google")
    fake_genai = types.ModuleType("google.genai")
    fake_types = types.ModuleType("google.genai.types")
    for name in ["GenerateContentConfig", "HttpOptions", "HttpRetryOptions"]:
        setattr(fake_types, name, lambda **kwargs: types.SimpleNamespace(**kwargs))
    fake_google.genai = fake_genai
    fake_genai.types = fake_types
    fake_modules = {
        "google": fake_google, "google.genai": fake_genai,
        "google.genai.types": fake_types,
    }
    chunks = [
        {"chunk_id": f"test_{i}", "pdf_page": 1, "printed_page": "1",
         "text": f"Test evidence {i}."}
        for i in range(1, 5)
    ]
    case = {"id": "TEST", "query": "What does the test evidence establish?"}

    def query_results(same_context: bool) -> list:
        return [{
            "case": case, "reranked_top10": chunks,
            "baseline_top3_ids": ["test_1", "test_2", "test_3"],
            "reranked_top3_ids": [
                "test_1", "test_2", "test_3" if same_context else "test_4",
            ],
        }]

    def run_generation(path, *, same_context=True, enabled=True, key=True, errors=()):
        if key:
            os.environ["GEMINI_API_KEY"] = FAKE_CREDENTIAL
        else:
            os.environ.pop("GEMINI_API_KEY", None)
        clients = []

        def create_client(**kwargs):
            assert kwargs["api_key"] == FAKE_CREDENTIAL
            client = FakeClient(errors)
            clients.append(client)
            return client

        fake_genai.Client = create_client
        namespace = {
            "query_results": query_results(same_context), "CONTEXT_K": 3,
            "RESULTS": path, "GEMINI_MODEL": "fake-test-model",
            "RUN_GEMINI": enabled, "runtime": {}, "hashlib": hashlib,
            "json": json, "os": os, "datetime": datetime, "timezone": timezone,
            "time": types.SimpleNamespace(perf_counter=time.perf_counter, sleep=lambda _: None),
        }
        execute_cell(generation, namespace)
        return namespace, clients

    # Patch both import surfaces and the credential. No .env is read, and all
    # outputs live in a temporary directory. Both patches restore prior state.
    with patch.dict(sys.modules, fake_modules), patch.dict(
        os.environ, {"GEMINI_API_KEY": FAKE_CREDENTIAL},
    ), tempfile.TemporaryDirectory(prefix="lma-runtime-tests-") as scratch:
        path = Path(scratch)
        namespace, clients = run_generation(path)
        assert len(namespace["answers"]) == 2
        assert len(clients) == 1 and clients[0].models.calls == 1 and clients[0].closed
        assert namespace["runtime"]["answers_generated_this_run"] == 2
        assert namespace["runtime"]["gemini_responses_generated_this_run"] == 1
        assert namespace["runtime"]["answers_reused_from_exact_request_cache"] == 0
        original_answers = namespace["answers"]
        namespace, clients = run_generation(path, key=False)
        assert len(namespace["answers"]) == 2 and not clients
        assert namespace["runtime"]["answers_reused_from_exact_request_cache"] == 2
        assert namespace["runtime"]["answers_generated_this_run"] == 0
        assert namespace["runtime"]["gemini_responses_generated_this_run"] == 0
        print("PASS: duplicate prompts produce two answer rows from one response; both rows reuse cache.")

        retry_path = path / "retry"
        retry_path.mkdir()
        namespace, clients = run_generation(retry_path, errors=[FakeAPIError(429)])
        assert clients[0].models.calls == 2 and clients[0].closed
        assert len(namespace["answers"]) == 2
        assert all(answer["attempts"] == 2 for answer in namespace["answers"])
        assert namespace["runtime"]["answers_generated_this_run"] == 2
        assert namespace["runtime"]["gemini_responses_generated_this_run"] == 1
        print("PASS: transient retry distinguishes attempts, successful responses, and answer rows.")

        partial_path = path / "partial"
        partial_path.mkdir()
        namespace, clients = run_generation(
            partial_path, same_context=False, enabled=False, key=False,
        )
        assert not namespace["answers"] and not clients
        first = namespace["request_specs"][0]
        (partial_path / "answer_cache.json").write_text(json.dumps({
            first["request_sha256"]: {
                "answer": "Previously cached answer.", "model_returned": "fake-test-model",
            },
        }))
        namespace, clients = run_generation(
            partial_path, same_context=False, enabled=False, key=False,
        )
        assert len(namespace["answers"]) == 1 and not clients
        assert namespace["answer_status"] == "not_run"
        assert namespace["runtime"]["answers_reused_from_exact_request_cache"] == 1
        namespace, clients = run_generation(partial_path, same_context=False, key=False)
        assert len(namespace["answers"]) == 1 and not clients
        assert namespace["answer_status"] == "awaiting_api_key"
        assert namespace["runtime"]["answers_generated_this_run"] == 0
        assert namespace["runtime"]["gemini_responses_generated_this_run"] == 0
        namespace, clients = run_generation(
            partial_path, same_context=False, errors=[FakeAPIError(401)],
        )
        assert len(namespace["answers"]) == 1 and namespace["answer_status"] == "api_error"
        assert clients[0].models.calls == 1 and clients[0].closed
        print("PASS: disabled, missing-key, and invalid-key paths preserve partial cache and report incomplete status.")

        review_path = path / "review"
        review_path.mkdir()
        review_namespace = {
            "RESULTS": review_path, "queries": [case],
            "query_results": query_results(True), "answers": original_answers,
            "display": lambda *args: None, "Markdown": lambda value: value,
            "pd": pd, "json": json, "hashlib": hashlib,
        }
        execute_cell(worksheet, review_namespace)
        review_csv = review_path / "answer_review.csv"
        rows = pd.read_csv(review_csv, dtype=str).fillna("")
        original_binding = rows.loc[0, "answer_fingerprints"]
        assert rows.loc[0, "review_status"] == "blank"
        rows.loc[0, "student_explanation"] = "Student-written retained note."
        rows.to_csv(review_csv, index=False)
        execute_cell(worksheet, review_namespace)
        assert pd.read_csv(review_csv).loc[0, "review_status"] == "current"
        review_namespace["answers"] = [
            dict(answer, answer=answer["answer"] + " Changed output.")
            if answer["variant"] == "baseline" else dict(answer)
            for answer in original_answers
        ]
        for _ in range(2):
            execute_cell(worksheet, review_namespace)
            rows = pd.read_csv(review_csv, dtype=str).fillna("")
            assert rows.loc[0, "review_status"] == "stale_preserved"
            assert rows.loc[0, "answer_fingerprints"] == original_binding
            assert rows.loc[0, "current_answer_fingerprints"] != original_binding
            assert rows.loc[0, "student_explanation"] == "Student-written retained note."
        print("PASS: stale student notes and original answer binding survive repeated reruns.")

    print("All runtime regression checks passed; no real API calls or project outputs written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
