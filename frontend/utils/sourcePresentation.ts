import type { RAGSource } from "../types/conversation";

const PDF_EXTENSION = /\.pdf$/i;
const WORD_SEPARATOR = /[_]+/g;
const TITLE_SEPARATOR = /\s+-\s+/;

export function completedSources(
  status: string,
  sources: RAGSource[],
): RAGSource[] | undefined {
  return status === "completed" && sources.length > 0 ? sources : undefined;
}

export function deduplicateSources(sources: RAGSource[]): RAGSource[] {
  const seen = new Set<string>();
  const unique: RAGSource[] = [];

  for (const source of sources) {
    const key = `${source.filename.trim().toLocaleLowerCase()}::${source.page_number ?? "none"}`;
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(source);
  }
  return unique;
}

export function formatSourceLabel(source: RAGSource): string {
  const filename = source.filename
    .replace(PDF_EXTENSION, "")
    .replace(WORD_SEPARATOR, " ")
    .trim();
  const [publisher, ...titleParts] = filename.split(TITLE_SEPARATOR);
  const title = titleParts.join(" — ").trim();
  const documentLabel = title ? `${publisher} — ${title}` : filename;
  return source.page_number !== null
    ? `${documentLabel}, p. ${source.page_number}`
    : documentLabel;
}
