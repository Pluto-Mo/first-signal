# IPO Evidence Intelligence

Personal A-share prospectus evidence reader.

## First-stage scope

The MVP reads local PDFs from `data/inbox/`, creates long-term document packages under `data/docs/`, generates evidence-backed reports, and serves them in a local Web reader.

## Local pipeline

These MVP commands are available now as CLI stubs. They will become fully functional as the parser, pipeline, and report generation implementation tasks land.

```powershell
python -m pip install -e ".[dev]"
python -m ipo_evidence.cli scan-inbox
python -m ipo_evidence.cli run --limit 3
python -m ipo_evidence.cli generate-report --doc-id <doc_id>
```

## Web reader

```powershell
npm install --prefix web
npm run web:dev
npm run web:build
```

## Data policy

`data/inbox/` contains user-owned PDF inputs. The system must not delete files in that directory.
Generated document packages under `data/docs/` are local artifacts and are not committed.
