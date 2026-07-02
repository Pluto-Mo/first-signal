import type { DocsIndexItem, ReaderBundle } from "./types";

function publicPath(path: string): string {
  const base = import.meta.env.BASE_URL || "/";
  const normalizedBase = base.endsWith("/") ? base : `${base}/`;
  const normalizedPath = path.replace(/^\/+/, "");
  return `${normalizedBase}${normalizedPath}`;
}

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(publicPath(path));

  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function loadDocsIndex(): Promise<DocsIndexItem[]> {
  return readJson<DocsIndexItem[]>("index.json");
}

export function loadReaderBundle(readerBundlePath: string): Promise<ReaderBundle> {
  return readJson<ReaderBundle>(readerBundlePath);
}
