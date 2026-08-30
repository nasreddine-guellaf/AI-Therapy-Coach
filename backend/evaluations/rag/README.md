# RAG evaluations

`dataset.json` contains 30 synthetic retrieval, grounding, multilingual, and
safety cases for the fixed three-PDF knowledge base. Populate or refine
`expected_source_ids` after the final licensed PDFs are indexed.

## Retrieval evaluation

The retrieval runner does not call an LLM. It measures vector retrieval,
thresholding, deduplication, accepted source IDs, per-chunk similarity scores,
and category pass rates:

```powershell
cd backend
python -m app.scripts.evaluate_rag
python -m app.scripts.evaluate_rag `
  --output evaluations/rag/latest_results.json
```

Use this mode to diagnose whether relevant chunks reach the application before
prompting or generation is involved.

## Generation evaluation

The generation runner exercises the full application flow:

```text
retrieval -> RAG context policy -> PromptBuilder -> configured LLM provider
          -> ResponseValidator -> final response and sources
```

It uses in-memory session and message repositories, so it does not write
synthetic evaluation cases to PostgreSQL. It uses the configured Qdrant,
embedding model, thresholds, and LLM provider.

```powershell
cd backend
python -m app.scripts.evaluate_generation_rag `
  --output evaluations/rag/latest_generation_results.json
```

For a quick smoke test that runs only the first case:

```powershell
python -m app.scripts.evaluate_generation_rag --limit 1
```

Add `--fail-on-mismatch` when the baseline is stable enough for CI. The command
returns a non-zero exit code when any evaluated case fails.

The runner never logs prompts, document text, generated answer text, API keys,
or conversation history. Console logs contain only case ID, category, status,
latency, chunk/source counts, and failure-reason categories. The JSON report
contains the synthetic dataset question because it is required for case review;
it intentionally omits full prompts, chunk text, and generated responses.

## Metric interpretation

- `overall_generation_success_rate`: cases passing every applicable check.
- `grounded_answer_success_rate`: answers with injected RAG context that
  completed with valid sources.
- `source_validity_rate`: validity of source-bearing answers against the exact
  metadata injected into `PromptBuilder`.
- `no_fake_source_rate`: cases with no invented structured source, source ID,
  or numeric page reference.
- `insufficient_context_disclosure_rate`: explicit document questions with no
  accepted context that clearly disclose document insufficiency.
- `general_fallback_correctness_rate`: safe non-document questions with empty
  RAG context that still complete through the LLM without sources.
- `medical_refusal_rate`: diagnosis or prescription questions that refuse the
  request and refer to a qualified professional.
- `crisis_handling_rate`: expected crisis/self-harm cases that bypass retrieval,
  prompting, and normal LLM generation.
- `average_latency_ms`: end-to-end mean latency per evaluated case.

`failure_reason` is a comma-separated set of stable categories suitable for
filtering. It contains no provider error details or response content.

## Tuning retrieval

Tune one variable at a time and compare both reports:

- Raise `RAG_MIN_SCORE` when unrelated chunks frequently appear in general
  questions. Lower it cautiously when clearly answerable questions retrieve
  nothing.
- Raise `RAG_DOCUMENT_QUESTION_MIN_SCORE` when explicit document questions are
  weakly grounded or show misleading sources. Lower it only when strong manual
  evidence shows that correct multilingual matches score below the threshold.
- Increase `RAG_TOP_K` when cross-document questions miss a relevant PDF. A
  larger value increases prompt size and the chance of including marginal
  context, so verify source validity and latency after every change.

Current defaults:

```env
RAG_MIN_SCORE=0.25
RAG_DOCUMENT_QUESTION_MIN_SCORE=0.35
RAG_TOP_K=4
```

Do not tune solely for a higher aggregate score. Review failed cases, source
metadata, safety rates, and language behavior together.
