# Human-annotation artifact

This directory is the self-contained human-validation artifact for the
execution-friction ($\Phi_t$) and bridging-strength ($\Delta_t$) coordinates.
It contains the frozen annotation instrument, anonymized individual labels,
the probe scores used for comparison, and the generated analyses reported by
the paper.

## Open the annotation instrument

Open `index.html` directly in a browser. No server or package installation is
required. Keep `index.html`, `app.js`, `styles.css`, and `dataset.js` together;
the interface loads the 60 Phi items and 160 Delta items from `dataset.js` and
stores progress locally in the browser.

`ANNOTATOR_README.txt` contains the short annotator instructions and
`RESEARCHER_GUIDE.md` records the sampling, blinding, collection, and analysis
protocol. The instructions are retained in the language used for the study.

## Released data

- `collected/`: six complete, individual annotation exports (three raters by
  two factors). `A01`--`A03` are study pseudonyms, not personal identifiers.
- `consensus_annotations.csv`: item-level human consensus and frozen probe
  comparison values.
- `reference/probe_scores.csv`: the minimal frozen probe-score input needed to
  rerun the analysis without unpublished model traces.
- `analysis_results.json` and `analysis_report.md`: machine-readable and
  human-readable analysis outputs.

The public individual exports retain labels, confidence, review flags, notes,
and elapsed seconds. Calendar dates and exact answer/update timestamps were
removed because they are unnecessary for reproducing the reported results.
The synthetic task text can contain fictional names or account details; these
are benchmark fixtures, not annotator information.

## Reproduce the analysis

The summary command uses only the Python standard library:

```bash
python3 human_annotations/scripts/analyze_annotations.py \
  human_annotations/collected/*.csv
```

Regenerate the detailed JSON, Markdown report, and consensus table:

```bash
python3 human_annotations/scripts/detailed_analysis.py \
  human_annotations/collected/*.csv
```

Run these commands from the repository root. The detailed analysis uses 5,000
deterministic cluster-bootstrap samples, so it can take several seconds.

## Scope

This release intentionally excludes the internal package-generation script,
raw model traces, legacy pilot annotations, browser caches, and the annotator
distribution archive. These are not needed to inspect the instrument or
reproduce the released human-validation statistics.
