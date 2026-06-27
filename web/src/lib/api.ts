import type { DocsIndexItem, ReaderBundle } from "./types";

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(path);

  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function loadDocsIndex(): Promise<DocsIndexItem[]> {
  return readJson<DocsIndexItem[]>("/index.json");
}

export function loadReaderBundle(readerBundlePath: string): Promise<ReaderBundle> {
  const normalizedPath = readerBundlePath.startsWith("/")
    ? readerBundlePath
    : `/${readerBundlePath}`;

  return readJson<ReaderBundle>(normalizedPath);
}
