"""Validate and summarize exported SubgoalBench human annotations."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from statistics import fmean

PACKAGE_DIR = Path(__file__).resolve().parents[1]
PROBE_SCORES = PACKAGE_DIR / "reference" / "probe_scores.csv"
LABEL_VALUE = {
    "phi": {"A": 0.0, "B": 0.25, "C": 0.5, "D": 0.75, "E": 1.0},
    "delta": {"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25, "E": 0.0},
}
CATEGORY = {label: index for index, label in enumerate("ABCDE")}


def read_rows(paths: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                row["_source_file"] = str(path)
                rows.append(row)
    return rows


def deduplicate(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    latest: dict[tuple[str, str, str], dict[str, str]] = {}
    duplicate_count = 0
    for row in rows:
        key = (row["annotator_id"], row["factor"], row["item_id"])
        if key in latest:
            duplicate_count += 1
            if row.get("updated_at", "") < latest[key].get("updated_at", ""):
                continue
        latest[key] = row
    return list(latest.values()), duplicate_count


def rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        average_rank = (start + end - 1) / 2 + 1
        for position in range(start, end):
            ranks[order[position]] = average_rank
        start = end
    return ranks


def pearson(x: list[float], y: list[float]) -> float:
    if len(x) < 2:
        return math.nan
    x_mean, y_mean = fmean(x), fmean(y)
    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y, strict=True))
    denominator = math.sqrt(sum((a - x_mean) ** 2 for a in x) * sum((b - y_mean) ** 2 for b in y))
    return numerator / denominator if denominator else math.nan


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(rank(x), rank(y))


def kendall_tau_b(x: list[float], y: list[float]) -> float:
    concordant = discordant = ties_x = ties_y = 0
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            dx, dy = x[i] - x[j], y[i] - y[j]
            if dx == 0 and dy == 0:
                ties_x += 1
                ties_y += 1
            elif dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif dx * dy > 0:
                concordant += 1
            else:
                discordant += 1
    denominator = math.sqrt((concordant + discordant + ties_x) * (concordant + discordant + ties_y))
    return (concordant - discordant) / denominator if denominator else math.nan


def _coincidence_matrix(labels_by_item: dict[str, list[str]]) -> tuple[list[list[float]], float]:
    coincidence = [[0.0] * 5 for _ in range(5)]
    for labels in labels_by_item.values():
        values = [CATEGORY[label] for label in labels]
        if len(values) < 2:
            continue
        counts = Counter(values)
        for left in range(5):
            for right in range(5):
                if left == right:
                    coincidence[left][right] += counts[left] * (counts[left] - 1) / (len(values) - 1)
                else:
                    coincidence[left][right] += counts[left] * counts[right] / (len(values) - 1)
    return coincidence, sum(map(sum, coincidence))


def _krippendorff_alpha(labels_by_item: dict[str, list[str]], *, ordinal: bool) -> float:
    coincidence, total = _coincidence_matrix(labels_by_item)
    if total <= 1:
        return math.nan
    marginals = [sum(row) for row in coincidence]

    def distance(left: int, right: int) -> float:
        if not ordinal:
            return ((left - right) / 4) ** 2
        lower, upper = sorted((left, right))
        cumulative = sum(marginals[lower : upper + 1])
        return (cumulative - (marginals[lower] + marginals[upper]) / 2) ** 2

    observed = sum(coincidence[i][j] * distance(i, j) for i in range(5) for j in range(5)) / total
    expected = sum(marginals[i] * marginals[j] * distance(i, j) for i in range(5) for j in range(5)) / (
        total * (total - 1)
    )
    return 1 - observed / expected if expected else math.nan


def krippendorff_alpha_ordinal(labels_by_item: dict[str, list[str]]) -> float:
    return _krippendorff_alpha(labels_by_item, ordinal=True)


def krippendorff_alpha_interval(labels_by_item: dict[str, list[str]]) -> float:
    """Alpha for the paper's explicitly equally spaced 0/.25/.5/.75/1 scores."""
    return _krippendorff_alpha(labels_by_item, ordinal=False)


def quadratic_weighted_kappa(human: list[str], probe: list[str]) -> float:
    matrix = [[0] * 5 for _ in range(5)]
    for left, right in zip(human, probe, strict=True):
        matrix[CATEGORY[left]][CATEGORY[right]] += 1
    count = len(human)
    if not count:
        return math.nan
    human_counts = [sum(row) for row in matrix]
    probe_counts = [sum(matrix[i][j] for i in range(5)) for j in range(5)]
    observed = expected = 0.0
    for i in range(5):
        for j in range(5):
            weight = ((i - j) / 4) ** 2
            observed += weight * matrix[i][j] / count
            expected += weight * human_counts[i] * probe_counts[j] / (count * count)
    return 1 - observed / expected if expected else math.nan


def modal_label(probabilities: dict[str, float]) -> str:
    return max("ABCDE", key=lambda label: (float(probabilities.get(label, 0.0)), -CATEGORY[label]))


def consensus_label(labels: list[str]) -> str:
    """Return the majority label, using the ordinal median when no majority exists."""
    counts = Counter(labels)
    most_common_count = max(counts.values())
    winners = [label for label, count in counts.items() if count == most_common_count]
    if len(winners) == 1:
        return winners[0]
    return sorted(labels, key=CATEGORY.__getitem__)[len(labels) // 2]


def probe_values(factor: str, rows: list[dict[str, str]]) -> dict[str, tuple[float, str]]:
    requested = {row["item_id"] for row in rows if row.get("factor") == factor}
    values: dict[str, tuple[float, str]] = {}
    with PROBE_SCORES.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["factor"] == factor and row["item_id"] in requested:
                values[row["item_id"]] = (float(row["probe_score"]), row["probe_modal_label"])
    missing = requested - values.keys()
    if missing:
        raise ValueError(f"Missing {factor} probe scores for: {', '.join(sorted(missing))}")
    return values


def summarize_factor(factor: str, rows: list[dict[str, str]], expected: int) -> None:
    factor_rows = [row for row in rows if row["factor"] == factor]
    annotators = sorted({row["annotator_id"] for row in factor_rows})
    print(f"\n{factor.upper()} ({expected} expected items per annotator)")
    for annotator in annotators:
        completed = sum(row.get("label") in CATEGORY for row in factor_rows if row["annotator_id"] == annotator)
        print(f"  {annotator}: {completed}/{expected}")

    valid = [row for row in factor_rows if row.get("label") in CATEGORY]
    if not valid:
        print("  no completed labels found")
        return
    by_item: dict[str, list[str]] = defaultdict(list)
    numeric_by_item: dict[str, list[float]] = defaultdict(list)
    for row in valid:
        by_item[row["item_id"]].append(row["label"])
        numeric_by_item[row["item_id"]].append(LABEL_VALUE[factor][row["label"]])
    comparable = {item_id: labels for item_id, labels in by_item.items() if len(labels) >= 2}
    exact_pairs = near_pairs = total_pairs = 0
    for labels in comparable.values():
        for left_index in range(len(labels)):
            for right_index in range(left_index + 1, len(labels)):
                distance = abs(CATEGORY[labels[left_index]] - CATEGORY[labels[right_index]])
                total_pairs += 1
                exact_pairs += distance == 0
                near_pairs += distance <= 1
    if total_pairs:
        print(f"  pairwise exact agreement: {exact_pairs / total_pairs:.1%}")
        print(f"  pairwise within-one agreement: {near_pairs / total_pairs:.1%}")
    print(f"  ordinal Krippendorff alpha: {krippendorff_alpha_ordinal(comparable):.3f}")
    print(f"  interval Krippendorff alpha: {krippendorff_alpha_interval(comparable):.3f}")

    probes = probe_values(factor, valid)
    complete_items = sorted(item_id for item_id in numeric_by_item if item_id in probes)
    human_scores = [fmean(numeric_by_item[item_id]) for item_id in complete_items]
    probe_scores = [probes[item_id][0] for item_id in complete_items]
    human_majority = [consensus_label(by_item[item_id]) for item_id in complete_items]
    probe_labels = [probes[item_id][1] for item_id in complete_items]
    mae = fmean(abs(human - probe) for human, probe in zip(human_scores, probe_scores, strict=True))
    print(f"  human-probe Spearman rho: {spearman(human_scores, probe_scores):.3f}")
    print(
        "  human-consensus/probe-modal quadratic weighted kappa: "
        f"{quadratic_weighted_kappa(human_majority, probe_labels):.3f}"
    )
    print(f"  mean absolute error: {mae:.3f}")

    if factor == "delta":
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        row_lookup = {row["item_id"]: row for row in valid}
        for item_id in complete_items:
            row = row_lookup[item_id]
            groups[(row["suite"], row["payload_key"])].append(item_id)
        taus = []
        for item_ids in groups.values():
            if len(item_ids) < 3:
                continue
            taus.append(
                kendall_tau_b(
                    [fmean(numeric_by_item[item_id]) for item_id in item_ids],
                    [probes[item_id][0] for item_id in item_ids],
                )
            )
        finite_taus = [value for value in taus if not math.isnan(value)]
        print(f"  mean within-payload Kendall tau-b: {fmean(finite_taus):.3f} (n={len(finite_taus)})")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_files", nargs="+", type=Path)
    args = parser.parse_args()
    rows, duplicate_count = deduplicate(read_rows(args.csv_files))
    manifest = json.loads((PACKAGE_DIR / "package_manifest.json").read_text())
    versions = sorted({row.get("package_version", "") for row in rows})
    if versions != [manifest["package_version"]]:
        raise SystemExit(f"Package version mismatch: {versions}")
    if duplicate_count:
        print(f"Kept the newest of {duplicate_count} duplicate exported rows.")
    summarize_factor("phi", rows, manifest["phi_item_count"])
    summarize_factor("delta", rows, manifest["delta_item_count"])


if __name__ == "__main__":
    main()
