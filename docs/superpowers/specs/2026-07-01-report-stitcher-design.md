# Report Stitcher Design

## Goal

Implement the next slice of `docs/report_generation_architecture.md`: make `report.md` come from qualified `SectionDraft` objects instead of the legacy long-form `report_generator.py` body, while preserving `citation.json`, `reader_bundle.json`, `analysis_log.json`, and existing document package behavior.

## Current State

Phase 1 already landed the dispatch and quality-control layers:

- `report_inputs.json` now carries `skill_refs`, `evidence_policy`, `output_contract`, and `section_role`.
- `section_generator.py` builds deterministic `SectionDraft` objects from `report_inputs` and `evidence_packet`.
- `quality_gate.py` classifies drafts as `include`, `merge`, or `log_only`, and executes `min_fact_count` plus `min_strength`.
- `analysis_log.py` writes skipped or merged section decisions into `analysis_log.json`.
- `pipeline.py` writes `analysis_log.json`, but `report.md` is still produced by `report_generator.py`.

The missing architecture step is the stitch layer:

```text
section_drafts + quality_decisions -> report_stitcher -> report.md
```

## Scope

This phase implements a deterministic local stitcher. It does not add LLM calls, external evidence, consumer-product-specific sections, or a full prompt runtime.

The stitcher will:

- Include only drafts whose `QualityGateDecision.action == "include"`.
- Exclude `merge` and `log_only` drafts from final `report.md`.
- Preserve citation ids exactly as emitted by `section_generator.py`.
- Preserve draft order from `report_inputs.section_groups[]`.
- Produce a readable Markdown report with one H1 title and one H2 per included section.
- Produce a short fallback report when no draft qualifies, using only non-factual wording without citation claims.

The pipeline will:

- Generate section drafts.
- Apply the quality gate.
- Build `analysis_log.json`.
- Build `report.md` through `report_stitcher.py`.
- Continue deriving `citation.json` directly from `evidence_packet`.
- Continue building `reader_bundle.json` from the final report and citations.

## Non-Goals

This phase will not:

- Delete `report_generator.py`.
- Add external evidence types.
- Add `quality_notes.md`.
- Add industry profile selection logic.
- Generate polished essay transitions with an LLM.
- Change citation numbering or citation source location rules.
- Change parser, evidence packet, table extraction, or Web reader behavior.

## Design

### `report_stitcher.py`

Create `src/ipo_evidence/report_stitcher.py` with a small interface:

```python
def stitch_report(
    company_name: str,
    drafts: list[SectionDraft],
    decisions: list[QualityGateDecision],
) -> str:
    ...
```

The function will return Markdown text ending with a newline.

The title format stays aligned with the existing report title:

```text
# {company_name}招股书长篇阅读
```

For each included draft, it writes:

```text
## {draft.title}

{draft.body}
```

If no draft is included, it writes:

```text
# {company_name}招股书长篇阅读

当前材料的可引用证据不足，暂不生成正文段落。请查看 analysis_log.json 获取需要补充的证据方向。
```

This fallback contains no factual company claims, so it does not need citations.

### Decision Lookup

The stitcher will build a `section_key -> QualityGateDecision` map. A draft enters the report only when its matching decision exists and has `action == "include"`.

If a draft has no matching decision, it is excluded. That is the safer default because a missing quality decision means the draft did not pass the quality gate.

### Citation Safety

The stitcher does not generate, renumber, or validate citations. It only moves `draft.body` into the final report. Citation numbering remains owned by:

```text
evidence_packet.items -> citation_layer.py
```

The implementation will add tests proving that citation ids remain unchanged in stitched output.

### Pipeline Integration

`pipeline._write_report_artifacts()` currently calls:

```python
report = generate_report(manifest.company_name, packet, report_inputs)
```

This phase will replace that report body source with:

```python
section_drafts = generate_section_drafts(packet, report_inputs)
quality_decisions = apply_quality_gate(section_drafts, _evidence_policies(report_inputs))
analysis_log = build_analysis_log(packet.doc_id, quality_decisions)
report = stitch_report(manifest.company_name, section_drafts, quality_decisions)
```

`build_citations(packet)` remains unchanged. `reader_bundle` continues to parse the final `report.md`.

### Legacy Report Generator

`report_generator.py` stays in the codebase for now. Existing focused tests for legacy report generation can remain, but pipeline tests should assert that the package report is produced through section drafts and quality decisions.

This avoids a large deletion and keeps a known fallback implementation available while the stitcher matures.

## Testing Strategy

Add focused tests for `report_stitcher.py`:

- It includes only `include` decisions.
- It excludes `merge` and `log_only` decisions.
- It preserves draft order.
- It preserves citation ids in draft bodies.
- It creates a citation-free fallback when no draft qualifies.

Add pipeline tests:

- `run_one()` writes a stitched report containing section titles from `report_inputs`.
- A section made weak by policy does not appear in `report.md` and appears in `analysis_log.json`.
- `reader_bundle.json` is built from stitched report sections.
- `citation.json` still starts at `C-001` and remains derived from `evidence_packet`.

Run full verification:

```powershell
python -m pytest -q
git diff --check
git status --short
```

Web tests are not required unless Web reader files change.

## Risks

The stitched report will initially be less essay-like than the legacy handwritten `report_generator.py`. That is acceptable for this phase because the architecture goal is to move final report assembly onto the section draft contract. Natural transitions can be improved later inside the stitch layer without changing citation or quality-gate boundaries.

The biggest correctness risk is accidentally including weak drafts in `report.md`. The design avoids that by making `include` the only action that enters the final report.

## Acceptance Criteria

- `src/ipo_evidence/report_stitcher.py` exists and is covered by focused tests.
- `pipeline._write_report_artifacts()` uses `stitch_report()` for `report.md`.
- `analysis_log.json` continues to record `merge` and `log_only` decisions.
- `citation.json` remains generated from `evidence_packet`.
- `reader_bundle.json` reflects stitched report sections.
- Full test suite passes.
