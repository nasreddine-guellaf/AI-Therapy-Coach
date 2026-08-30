# RAG evaluation baseline

`dataset.json` contains 30 retrieval and safety cases. It deliberately evaluates
expected behavior rather than exact generated answers.

The product uses hybrid fallback behavior: an unanswerable case succeeds when
no chunk is accepted as document evidence. The live conversation may still
provide safe general coaching, but must return no sources and must disclose
document insufficiency for an explicit document question.

After the three licensed PDFs are finalized, replace or refine the sample
questions and populate `expected_source_ids` using the stable source IDs
returned by ingestion/retrieval.

Run from `backend` after Qdrant and ingestion:

```powershell
python -m app.scripts.evaluate_rag
```

To write a machine-readable report:

```powershell
python -m app.scripts.evaluate_rag --output evaluations/rag/latest_results.json
```

Use `--fail-on-mismatch` in CI once the dataset has been curated against the
final PDFs.

The JSON report includes each retrieved chunk's score and acceptance flag,
`max_score`, `min_score`, `average_score`, and pass scores for answerable,
cross-document, multilingual, unanswerable, and safety categories.
