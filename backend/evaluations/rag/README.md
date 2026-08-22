# RAG evaluation baseline

`dataset.json` contains 30 retrieval and safety cases. It deliberately evaluates
expected behavior rather than exact generated answers.

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

