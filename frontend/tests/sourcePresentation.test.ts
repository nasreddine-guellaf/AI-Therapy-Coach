import assert from "node:assert/strict";
import test from "node:test";

import type { RAGSource } from "../types/conversation";
import {
  completedSources,
  deduplicateSources,
  formatSourceLabel,
} from "../utils/sourcePresentation";

const source = (sourceId: string, pageNumber: number | null): RAGSource => ({
  source_id: sourceId,
  filename: "OMS - Faire ce qui compte en période de stress.pdf",
  page_number: pageNumber,
  chunk_index: 1,
  score: 0.9,
});

test("deduplicates repeated sources from the same file and page", () => {
  const result = deduplicateSources([
    source("chunk-1", 132),
    source("chunk-2", 132),
    source("chunk-3", 133),
  ]);
  assert.deepEqual(result.map((item) => item.source_id), ["chunk-1", "chunk-3"]);
});

test("formats a reader-facing source label without its raw id", () => {
  assert.equal(
    formatSourceLabel(source("raw-technical-id", 132)),
    "OMS — Faire ce qui compte en période de stress, p. 132",
  );
});

test("returns sources only for a completed answer", () => {
  const sources = [source("chunk-1", 132)];
  assert.deepEqual(completedSources("completed", sources), sources);
  assert.equal(completedSources("llm_incomplete", sources), undefined);
  assert.equal(completedSources("llm_unavailable", sources), undefined);
  assert.equal(completedSources("validation_failed", sources), undefined);
});
