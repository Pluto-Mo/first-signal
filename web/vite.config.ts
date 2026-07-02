import { readFile } from "node:fs/promises";
import path from "node:path";
import { defineConfig, type Plugin, type ViteDevServer } from "vite";
import react from "@vitejs/plugin-react";

function contentTypeFor(filePath: string): string {
  const extension = path.extname(filePath).toLowerCase();

  switch (extension) {
    case ".json":
      return "application/json; charset=utf-8";
    case ".md":
      return "text/markdown; charset=utf-8";
    case ".txt":
      return "text/plain; charset=utf-8";
    case ".pdf":
      return "application/pdf";
    default:
      return "application/octet-stream";
  }
}

function serveDocsDirectory(docsDir: string): Plugin {
  const rootDir = path.resolve(docsDir);

  return {
    name: "serve-docs-directory",
    configureServer(server: ViteDevServer) {
      server.middlewares.use(async (req, res, next) => {
        if (req.method !== "GET" && req.method !== "HEAD") {
          next();
          return;
        }

        const requestPath = (req.url ?? "/").split("?")[0];
        if (
          requestPath === "/" ||
          requestPath.startsWith("/src/") ||
          requestPath.startsWith("/@") ||
          requestPath.startsWith("/node_modules/") ||
          requestPath.startsWith("/assets/")
        ) {
          next();
          return;
        }

        let relativePath: string;
        try {
          relativePath = decodeURIComponent(requestPath.replace(/^\/+/, ""));
        } catch {
          next();
          return;
        }

        const resolvedPath = path.resolve(rootDir, relativePath);
        const rootRelativePath = path.relative(rootDir, resolvedPath);

        if (rootRelativePath.startsWith("..") || path.isAbsolute(rootRelativePath)) {
          next();
          return;
        }

        try {
          const body = await readFile(resolvedPath);
          res.setHeader("Content-Type", contentTypeFor(resolvedPath));
          res.end(req.method === "HEAD" ? undefined : body);
          return;
        } catch {
          next();
        }
      });
    }
  };
}

export default defineConfig(({ command }) => {
  const devDocsDir = path.resolve(__dirname, "../data/docs");
  const showcaseDocsDir = path.resolve(__dirname, "showcase-data");
  const docsDir = path.resolve(
    process.env.READER_DATA_DIR ?? (command === "build" ? showcaseDocsDir : devDocsDir)
  );

  return {
    publicDir: docsDir,
    plugins: [react(), serveDocsDirectory(docsDir)],
    test: {
      environment: "jsdom",
      globals: true
    }
  };
});
