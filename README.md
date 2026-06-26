# IPO Evidence Intelligence

Personal A-share prospectus evidence reader.

## First-stage scope

The MVP reads local PDFs from `data/inbox/`, creates long-term document packages under `data/docs/`, generates evidence-backed reports, and serves them in a local Web reader.

## Local pipeline

The local MVP pipeline scans PDFs from `data/inbox/`, builds document packages under `data/docs/`, and can regenerate report artifacts from an existing package.

```powershell
python -m pip install -e ".[dev]"
python -m ipo_evidence.cli scan-inbox
python -m ipo_evidence.cli run --limit 3
python -m ipo_evidence.cli generate-report --doc-id <doc_id>
```

## Web reader

The Web reader is a local Vite React app focused on continuous report reading with citation details on the right side.

```powershell
npm install --prefix web
npm run web:dev
npm run web:build
```

## Verified MVP commands

```powershell
python -m pytest -q
npm --prefix web run test
npm --prefix web run build
python -m ipo_evidence.cli run --limit 1
```

## A-share source sync

```powershell
python -m ipo_evidence.source_sync.cli sync-a-share --days 7 --limit 3
```

This command discovers a small number of recent A-share prospectus candidates, filters out non-body or blacklisted samples, and downloads allowed PDFs into `data/inbox/` without automatically triggering OCR.

## Data policy

`data/inbox/` contains user-owned PDF inputs. The system must not delete files in that directory.
Generated document packages under `data/docs/` are local artifacts and are not committed.
