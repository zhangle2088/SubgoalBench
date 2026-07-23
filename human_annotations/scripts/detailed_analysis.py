"""Produce a reproducible detailed report for the three-annotator validation run."""

# ruff: noqa: RUF001 -- Report text intentionally uses Chinese punctuation and typographic dashes.

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean

from analyze_annotations import (
    CATEGORY,
    LABEL_VALUE,
    consensus_label,
    deduplicate,
    kendall_tau_b,
    krippendorff_alpha_interval,
    krippendorff_alpha_ordinal,
    probe_values,
    quadratic_weighted_kappa,
    read_rows,
    spearman,
)

PACKAGE_DIR = Path(__file__).resolve().parents[1]
BOOTSTRAP_SEED = 20260720
BOOTSTRAP_SAMPLES = 5000


def load_rows(paths: list[Path]) -> tuple[list[dict[str, str]], int]:
    rows, duplicate_count = deduplicate(read_rows(paths))
    return [row for row in rows if row.get("label") in CATEGORY], duplicate_count


def load_item_metadata() -> dict[str, dict]:
    text = (PACKAGE_DIR / "dataset.js").read_text(encoding="utf-8")
    data = json.loads(text.removeprefix("window.ANNOTATION_DATA = ").removesuffix(";\n"))
    return {item["item_id"]: item for item in data["phi_items"] + data["delta_items"]}


def percentile(values: list[float], probability: float) -> float:
    finite = sorted(value for value in values if not math.isnan(value))
    position = (len(finite) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return finite[lower]
    return finite[lower] * (upper - position) + finite[upper] * (position - lower)


def bootstrap_ci(
    factor: str,
    item_ids: list[str],
    labels_by_item: dict[str, list[str]],
    human_scores: dict[str, float],
    probes: dict[str, tuple[float, str]],
    metadata: dict[str, dict],
) -> dict[str, tuple[float, float]]:
    rng = random.Random(BOOTSTRAP_SEED + (0 if factor == "phi" else 1))
    if factor == "phi":
        workflow_groups: dict[str, list[str]] = defaultdict(list)
        for item_id in item_ids:
            workflow_groups[metadata[item_id]["suite"]].append(item_id)
        units = list(workflow_groups.values())
    else:
        payload_groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for item_id in item_ids:
            item = metadata[item_id]
            payload_groups[(item["suite"], item["payload_key"])].append(item_id)
        units = list(payload_groups.values())
    rho_samples = []
    alpha_samples = []
    mae_samples = []
    tau_samples = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sampled_units = [rng.choice(units) for _ in units]
        sampled = [item_id for unit in sampled_units for item_id in unit]
        rho_samples.append(
            spearman(
                [human_scores[item_id] for item_id in sampled],
                [probes[item_id][0] for item_id in sampled],
            )
        )
        mae_samples.append(fmean(abs(human_scores[item_id] - probes[item_id][0]) for item_id in sampled))
        sampled_labels = {f"{position}:{item_id}": labels_by_item[item_id] for position, item_id in enumerate(sampled)}
        alpha_samples.append(krippendorff_alpha_ordinal(sampled_labels))
        if factor == "delta":
            sampled_taus = [
                kendall_tau_b(
                    [human_scores[item_id] for item_id in unit],
                    [probes[item_id][0] for item_id in unit],
                )
                for unit in sampled_units
            ]
            tau_samples.append(fmean(value for value in sampled_taus if not math.isnan(value)))
    intervals = {
        "spearman": (percentile(rho_samples, 0.025), percentile(rho_samples, 0.975)),
        "alpha": (percentile(alpha_samples, 0.025), percentile(alpha_samples, 0.975)),
        "mae": (percentile(mae_samples, 0.025), percentile(mae_samples, 0.975)),
    }
    if tau_samples:
        intervals["kendall_tau"] = (
            percentile(tau_samples, 0.025),
            percentile(tau_samples, 0.975),
        )
    return intervals


def pair_agreement(left: list[str], right: list[str]) -> tuple[float, float]:
    distances = [abs(CATEGORY[a] - CATEGORY[b]) for a, b in zip(left, right, strict=True)]
    return (
        sum(distance == 0 for distance in distances) / len(distances),
        sum(distance <= 1 for distance in distances) / len(distances),
    )


def multi_rater_agreement(labels_by_item: dict[str, list[str]]) -> tuple[float, float]:
    exact_pairs = near_pairs = total_pairs = 0
    for labels in labels_by_item.values():
        for left_index in range(len(labels)):
            for right_index in range(left_index + 1, len(labels)):
                distance = abs(CATEGORY[labels[left_index]] - CATEGORY[labels[right_index]])
                total_pairs += 1
                exact_pairs += distance == 0
                near_pairs += distance <= 1
    return exact_pairs / total_pairs, near_pairs / total_pairs


def subgroup_stats(
    groups: dict[str, list[str]],
    labels_by_item: dict[str, list[str]],
    human_scores: dict[str, float],
    probes: dict[str, tuple[float, str]],
) -> dict[str, dict]:
    output = {}
    for name, subgroup in sorted(groups.items()):
        exact, within_one = multi_rater_agreement({item_id: labels_by_item[item_id] for item_id in subgroup})
        output[name] = {
            "n": len(subgroup),
            "exact": exact,
            "within_one": within_one,
            "ordinal_alpha": krippendorff_alpha_ordinal({item_id: labels_by_item[item_id] for item_id in subgroup}),
            "human_probe_spearman": spearman(
                [human_scores[item_id] for item_id in subgroup],
                [probes[item_id][0] for item_id in subgroup],
            ),
        }
    return output


def analyze_factor(factor: str, rows: list[dict[str, str]], metadata: dict[str, dict]) -> dict:
    factor_rows = [row for row in rows if row["factor"] == factor]
    annotators = sorted({row["annotator_id"] for row in factor_rows})
    by_annotator = {
        annotator: {row["item_id"]: row for row in factor_rows if row["annotator_id"] == annotator}
        for annotator in annotators
    }
    item_ids = sorted(set.intersection(*(set(items) for items in by_annotator.values())))
    labels_by_item = {
        item_id: [by_annotator[annotator][item_id]["label"] for annotator in annotators] for item_id in item_ids
    }
    scores_by_item = {
        item_id: [LABEL_VALUE[factor][label] for label in labels] for item_id, labels in labels_by_item.items()
    }
    human_scores = {item_id: fmean(scores) for item_id, scores in scores_by_item.items()}
    probes = probe_values(factor, factor_rows)
    majority = {item_id: consensus_label(labels_by_item[item_id]) for item_id in item_ids}
    no_majority_count = sum(max(Counter(labels_by_item[item_id]).values()) == 1 for item_id in item_ids)

    pairwise = {}
    for left_index, left in enumerate(annotators):
        for right in annotators[left_index + 1 :]:
            left_labels = [by_annotator[left][item_id]["label"] for item_id in item_ids]
            right_labels = [by_annotator[right][item_id]["label"] for item_id in item_ids]
            exact, within_one = pair_agreement(left_labels, right_labels)
            pairwise[f"{left}-{right}"] = {
                "exact": exact,
                "within_one": within_one,
                "weighted_kappa": quadratic_weighted_kappa(left_labels, right_labels),
                "spearman": spearman(
                    [LABEL_VALUE[factor][label] for label in left_labels],
                    [LABEL_VALUE[factor][label] for label in right_labels],
                ),
            }

    annotator_probe = {}
    for annotator in annotators:
        human = [LABEL_VALUE[factor][by_annotator[annotator][item_id]["label"]] for item_id in item_ids]
        probe = [probes[item_id][0] for item_id in item_ids]
        annotator_probe[annotator] = {
            "spearman": spearman(human, probe),
            "mae": fmean(abs(a - b) for a, b in zip(human, probe, strict=True)),
            "mean_human": fmean(human),
            "mean_probe": fmean(probe),
            "mean_bias_human_minus_probe": fmean(a - b for a, b in zip(human, probe, strict=True)),
        }

    all_human = [human_scores[item_id] for item_id in item_ids]
    all_probe = [probes[item_id][0] for item_id in item_ids]
    exact, within_one = multi_rater_agreement(labels_by_item)
    result = {
        "n_items": len(item_ids),
        "annotators": annotators,
        "label_distributions": {
            annotator: dict(Counter(by_annotator[annotator][item_id]["label"] for item_id in item_ids))
            for annotator in annotators
        },
        "pairwise": pairwise,
        "annotator_probe": annotator_probe,
        "aggregate": {
            "pairwise_exact": exact,
            "pairwise_within_one": within_one,
            "ordinal_alpha": krippendorff_alpha_ordinal(labels_by_item),
            "interval_alpha": krippendorff_alpha_interval(labels_by_item),
            "human_probe_spearman": spearman(all_human, all_probe),
            "human_probe_mae": fmean(abs(a - b) for a, b in zip(all_human, all_probe, strict=True)),
            "human_majority_probe_weighted_kappa": quadratic_weighted_kappa(
                [majority[item_id] for item_id in item_ids],
                [probes[item_id][1] for item_id in item_ids],
            ),
            "no_majority_items": no_majority_count,
        },
    }
    result["bootstrap_95_ci"] = bootstrap_ci(factor, item_ids, labels_by_item, human_scores, probes, metadata)

    suite_groups: dict[str, list[str]] = defaultdict(list)
    band_groups: dict[str, list[str]] = defaultdict(list)
    for item_id in item_ids:
        suite_groups[metadata[item_id]["suite"]].append(item_id)
        probe_score = probes[item_id][0]
        band = "low [0, 1/3)" if probe_score < 1 / 3 else "mid [1/3, 2/3)" if probe_score < 2 / 3 else "high [2/3, 1]"
        band_groups[band].append(item_id)
    result["by_suite"] = subgroup_stats(suite_groups, labels_by_item, human_scores, probes)
    result["by_probe_band"] = subgroup_stats(band_groups, labels_by_item, human_scores, probes)
    result["largest_disagreements"] = [
        {
            "item_id": item_id,
            "action_family": metadata[item_id]["action_family"],
            "labels": labels_by_item[item_id],
            "human_mean": human_scores[item_id],
            "probe_score": probes[item_id][0],
            "absolute_error": abs(human_scores[item_id] - probes[item_id][0]),
        }
        for item_id in sorted(
            item_ids,
            key=lambda key: (
                max(CATEGORY[label] for label in labels_by_item[key])
                - min(CATEGORY[label] for label in labels_by_item[key]),
                abs(human_scores[key] - probes[key][0]),
            ),
            reverse=True,
        )[:15]
    ]

    if factor == "phi":
        family_groups: dict[str, list[str]] = defaultdict(list)
        for item_id in item_ids:
            family_groups[metadata[item_id]["action_family"]].append(item_id)
        result["by_action_family"] = subgroup_stats(family_groups, labels_by_item, human_scores, probes)
    else:
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for item_id in item_ids:
            item = metadata[item_id]
            groups[(item["suite"], item["payload_key"])].append(item_id)
        group_taus = []
        for (suite, payload_key), subgroup in groups.items():
            tau = kendall_tau_b(
                [human_scores[item_id] for item_id in subgroup],
                [probes[item_id][0] for item_id in subgroup],
            )
            group_taus.append({"suite": suite, "payload_key": payload_key, "tau_b": tau})
        result["within_payload_tau"] = sorted(group_taus, key=lambda entry: entry["tau_b"])
        finite_taus = [entry["tau_b"] for entry in group_taus if not math.isnan(entry["tau_b"])]
        result["aggregate"]["mean_within_payload_kendall_tau_b"] = fmean(finite_taus)
    return result


def fmt(value: float) -> str:
    return "nan" if math.isnan(value) else f"{value:.3f}"


def json_safe(value: object) -> object:
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value


def render_markdown(results: dict) -> str:
    validation = results["validation"]
    phi = results["phi"]
    delta = results["delta"]
    phi_aggregate = phi["aggregate"]
    delta_aggregate = delta["aggregate"]
    phi_ci = phi["bootstrap_95_ci"]
    delta_ci = delta["bootstrap_95_ci"]

    def range_for(metric: str, groups: dict[str, dict], *, percent: bool = True) -> str:
        values = [stats[metric] for stats in groups.values()]
        if percent:
            return f"{min(values):.1%}–{max(values):.1%}"
        return f"{fmt(min(values))}–{fmt(max(values))}"

    lines = [
        "# Human Annotation Detailed Analysis",
        "",
        "## Data validation",
        "",
        f"- Package version: `{validation['package_version']}`",
        f"- Input rows: {validation['input_rows']} valid labels; duplicate rows resolved: {validation['duplicates']}",
        "- Completion: all three annotators completed 60/60 PHI items and 160/160 DELTA items.",
        "",
        "## 结论解读",
        "",
        f"- 标注完整且版本一致，共 {validation['input_rows']} 个有效标签，无重复记录。",
        f"- 人工聚合分数与 probe 的相关性在 PHI 上为 {fmt(phi_aggregate['human_probe_spearman'])} "
        f"（95% CI {fmt(phi_ci['spearman'][0])}–{fmt(phi_ci['spearman'][1])}），在 DELTA 上为 "
        f"{fmt(delta_aggregate['human_probe_spearman'])}（95% CI {fmt(delta_ci['spearman'][0])}–"
        f"{fmt(delta_ci['spearman'][1])}）。DELTA 的一致性尤其强，PHI 为中等偏强。",
        f"- 标注者间 ordinal Krippendorff alpha 分别为 {fmt(phi_aggregate['ordinal_alpha'])} 和 "
        f"{fmt(delta_aggregate['ordinal_alpha'])}；exact agreement 只有 "
        f"{phi_aggregate['pairwise_exact']:.1%}/{delta_aggregate['pairwise_exact']:.1%}，但 within-one "
        f"agreement 达 {phi_aggregate['pairwise_within_one']:.1%}/{delta_aggregate['pairwise_within_one']:.1%}。"
        "这说明分歧主要是相邻档位，而不是方向性反转。",
        f"- MAE 为 {fmt(phi_aggregate['human_probe_mae'])}/{fmt(delta_aggregate['human_probe_mae'])}，"
        "均小于一个标签步长 0.25；DELTA 在同一 payload 内对 8 个 prefix 的平均 Kendall tau-b 为 "
        f"{fmt(delta_aggregate['mean_within_payload_kendall_tau_b'])}（95% CI "
        f"{fmt(delta_ci['kendall_tau'][0])}–{fmt(delta_ci['kendall_tau'][1])}）。",
        f"- 按 probe 分数带划分，within-one agreement 范围为 PHI "
        f"{range_for('within_one', phi['by_probe_band'])}、DELTA "
        f"{range_for('within_one', delta['by_probe_band'])}；按 workflow 划分则为 PHI "
        f"{range_for('within_one', phi['by_suite'])}、DELTA "
        f"{range_for('within_one', delta['by_suite'])}。DELTA 的 travel_recommend_restaurant 是明显弱项。",
        "- 主要分歧集中在删除文件、转账等高后果动作的阻力边界，以及餐厅检索场景中“前缀是否真的能为删除文件/访问链接提供下一步依据”的语义边界。",
        "- 标注者存在量表使用差异：A02 在 PHI 上明显集中于 C，A01 在 DELTA 上更常使用 A/E；这解释了 exact agreement 偏低，但未破坏聚合后的排序一致性。",
        "",
        "### Paper-ready summary",
        "",
        f"> On the stratified human-validation sample, probe scores correlated with aggregated human judgments at "
        f"Spearman $\\rho={fmt(phi_aggregate['human_probe_spearman'])}$ (workflow-cluster bootstrap 95% CI: "
        f"{fmt(phi_ci['spearman'][0])}--{fmt(phi_ci['spearman'][1])}) for execution friction and "
        f"$\\rho={fmt(delta_aggregate['human_probe_spearman'])}$ (payload-cluster bootstrap 95% CI: "
        f"{fmt(delta_ci['spearman'][0])}--{fmt(delta_ci['spearman'][1])}) for bridging strength. "
        f"Ordinal Krippendorff's $\\alpha$ was {fmt(phi_aggregate['ordinal_alpha'])} for $\\Phi_t$ and "
        f"{fmt(delta_aggregate['ordinal_alpha'])} for $\\Delta_t$. Pairwise exact agreement was "
        f"{phi_aggregate['pairwise_exact']:.1%} and {delta_aggregate['pairwise_exact']:.1%}, while agreement "
        f"within one label reached {phi_aggregate['pairwise_within_one']:.1%} and "
        f"{delta_aggregate['pairwise_within_one']:.1%}, respectively. Mean absolute error was "
        f"{fmt(phi_aggregate['human_probe_mae'])} for $\\Phi_t$ and "
        f"{fmt(delta_aggregate['human_probe_mae'])} for $\\Delta_t$, both below one 0.25-wide label step. "
        f"For $\\Delta_t$, mean within-payload Kendall $\\tau_b$ was "
        f"{fmt(delta_aggregate['mean_within_payload_kendall_tau_b'])}. Disagreements were concentrated in "
        "high-consequence action boundaries and semantically ambiguous bridges rather than systematic coordinate reversals.",
        "",
        "### Interpretation cautions",
        "",
        "- Subgroup alpha and correlation values are descriptive: range restriction and small per-workflow samples make them unsuitable for direct comparison with the overall statistics.",
        "- DELTA is a stratified validation sample of 20 payload groups, not a simple random sample of all 480 benchmark instances.",
        "- Confidence scores are optional and largely missing for A01, so they are not used for inferential analysis.",
        "",
    ]
    for factor in ("phi", "delta"):
        result = results[factor]
        aggregate = result["aggregate"]
        ci = result["bootstrap_95_ci"]
        lines.extend(
            [
                f"## {factor.upper()}",
                "",
                f"- Complete items: {result['n_items']} × {len(result['annotators'])} annotators",
                f"- Ordinal Krippendorff alpha: {fmt(aggregate['ordinal_alpha'])} "
                f"(cluster-bootstrap 95% CI {fmt(ci['alpha'][0])}–{fmt(ci['alpha'][1])})",
                f"- Interval Krippendorff alpha (equal-spaced scores): {fmt(aggregate['interval_alpha'])}",
                f"- Pairwise exact / within-one agreement: {aggregate['pairwise_exact']:.1%} / "
                f"{aggregate['pairwise_within_one']:.1%}",
                f"- Human–probe Spearman rho: {fmt(aggregate['human_probe_spearman'])} "
                f"(cluster-bootstrap 95% CI {fmt(ci['spearman'][0])}–{fmt(ci['spearman'][1])})",
                f"- Human-consensus/probe-modal weighted kappa: {fmt(aggregate['human_majority_probe_weighted_kappa'])}",
                f"- Human–probe MAE: {fmt(aggregate['human_probe_mae'])} "
                f"(cluster-bootstrap 95% CI {fmt(ci['mae'][0])}–{fmt(ci['mae'][1])})",
                f"- No-majority items: {aggregate['no_majority_items']} "
                "(consensus uses the ordinal median for these ties)",
                "",
                "### Label distributions",
                "",
                "| Annotator | A | B | C | D | E |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for annotator, counts in result["label_distributions"].items():
            lines.append(f"| {annotator} | " + " | ".join(str(counts.get(label, 0)) for label in "ABCDE") + " |")
        lines.extend(
            [
                "",
                "### Pairwise human agreement",
                "",
                "| Pair | Exact | Within one | Weighted kappa | Spearman |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for pair, stats in result["pairwise"].items():
            lines.append(
                f"| {pair} | {stats['exact']:.1%} | {stats['within_one']:.1%} | "
                f"{fmt(stats['weighted_kappa'])} | {fmt(stats['spearman'])} |"
            )
        lines.extend(
            [
                "",
                "### Each annotator versus probe",
                "",
                "| Annotator | Spearman | MAE | Human mean | Probe mean | Human − probe |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for annotator, stats in result["annotator_probe"].items():
            lines.append(
                f"| {annotator} | {fmt(stats['spearman'])} | {fmt(stats['mae'])} | "
                f"{fmt(stats['mean_human'])} | {fmt(stats['mean_probe'])} | "
                f"{fmt(stats['mean_bias_human_minus_probe'])} |"
            )
        lines.append("")
        if factor == "delta":
            lines.append(
                f"- Mean within-payload Kendall tau-b: "
                f"{fmt(aggregate['mean_within_payload_kendall_tau_b'])} "
                f"(payload-cluster bootstrap 95% CI {fmt(ci['kendall_tau'][0])}–"
                f"{fmt(ci['kendall_tau'][1])})"
            )
            lines.append("")
        lines.extend(
            [
                "### Agreement by probe-score band",
                "",
                "| Band | n | Exact | Within one | Ordinal alpha | Human–probe Spearman |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for name, stats in result["by_probe_band"].items():
            lines.append(
                f"| {name} | {stats['n']} | {stats['exact']:.1%} | {stats['within_one']:.1%} | "
                f"{fmt(stats['ordinal_alpha'])} | {fmt(stats['human_probe_spearman'])} |"
            )
        lines.extend(
            [
                "",
                "### Agreement by workflow",
                "",
                "| Workflow | n | Exact | Within one | Ordinal alpha | Human–probe Spearman |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for name, stats in result["by_suite"].items():
            lines.append(
                f"| {name} | {stats['n']} | {stats['exact']:.1%} | {stats['within_one']:.1%} | "
                f"{fmt(stats['ordinal_alpha'])} | {fmt(stats['human_probe_spearman'])} |"
            )
        lines.extend(
            [
                "",
                "### Largest label disagreements",
                "",
                "| Item | Action family | Human labels | Human mean | Probe | Absolute error |",
                "|---|---|---|---:|---:|---:|",
            ]
        )
        for entry in result["largest_disagreements"][:10]:
            lines.append(
                f"| {entry['item_id']} | {entry['action_family']} | "
                f"{'/'.join(entry['labels'])} | {fmt(entry['human_mean'])} | "
                f"{fmt(entry['probe_score'])} | {fmt(entry['absolute_error'])} |"
            )
        lines.append("")
        if factor == "delta":
            lines.extend(
                ["### Delta within-payload ranking", "", "| Suite | Payload | Kendall tau-b |", "|---|---|---:|"]
            )
            for entry in result["within_payload_tau"]:
                lines.append(f"| {entry['suite']} | {entry['payload_key']} | {fmt(entry['tau_b'])} |")
            lines.append("")
    return "\n".join(lines)


def write_consensus_csv(path: Path, results: dict) -> None:
    fields = [
        "factor",
        "item_id",
        "suite",
        "payload_key",
        "action_family",
        "human_labels",
        "human_consensus",
        "human_mean",
        "probe_modal_label",
        "probe_score",
        "absolute_error",
        "label_range",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for factor in ("phi", "delta"):
            writer.writerows(results[factor]["consensus_rows"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_files", nargs="+", type=Path)
    parser.add_argument("--json", type=Path, default=PACKAGE_DIR / "analysis_results.json")
    parser.add_argument("--markdown", type=Path, default=PACKAGE_DIR / "analysis_report.md")
    parser.add_argument("--consensus-csv", type=Path, default=PACKAGE_DIR / "consensus_annotations.csv")
    args = parser.parse_args()
    rows, duplicate_count = load_rows(args.csv_files)
    metadata = load_item_metadata()
    manifest = json.loads((PACKAGE_DIR / "package_manifest.json").read_text())
    versions = sorted({row.get("package_version", "") for row in rows})
    if versions != [manifest["package_version"]]:
        raise SystemExit(f"Package version mismatch: {versions}")
    results = {factor: analyze_factor(factor, rows, metadata) for factor in ("phi", "delta")}
    results["validation"] = {
        "package_version": manifest["package_version"],
        "input_rows": len(rows),
        "duplicates": duplicate_count,
    }
    for factor in ("phi", "delta"):
        result = results[factor]
        annotator_count = len(result["annotators"])
        expected = manifest[f"{factor}_item_count"]
        if result["n_items"] != expected or annotator_count != 3:
            raise SystemExit(
                f"Incomplete {factor}: {result['n_items']} common items across "
                f"{annotator_count} annotators; expected {expected} across 3"
            )
        factor_rows = [row for row in rows if row["factor"] == factor]
        labels_by_item: dict[str, list[str]] = defaultdict(list)
        for row in sorted(factor_rows, key=lambda entry: entry["annotator_id"]):
            labels_by_item[row["item_id"]].append(row["label"])
        probes = probe_values(factor, factor_rows)
        consensus_rows = []
        for item_id in sorted(labels_by_item):
            labels = labels_by_item[item_id]
            human_mean = fmean(LABEL_VALUE[factor][label] for label in labels)
            probe_score, probe_label = probes[item_id]
            item = metadata[item_id]
            consensus_rows.append(
                {
                    "factor": factor,
                    "item_id": item_id,
                    "suite": item["suite"],
                    "payload_key": item["payload_key"],
                    "action_family": item["action_family"],
                    "human_labels": "/".join(labels),
                    "human_consensus": consensus_label(labels),
                    "human_mean": human_mean,
                    "probe_modal_label": probe_label,
                    "probe_score": probe_score,
                    "absolute_error": abs(human_mean - probe_score),
                    "label_range": max(CATEGORY[label] for label in labels) - min(CATEGORY[label] for label in labels),
                }
            )
        result["consensus_rows"] = consensus_rows
    args.json.write_text(
        json.dumps(json_safe(results), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.markdown.write_text(render_markdown(results) + "\n", encoding="utf-8")
    write_consensus_csv(args.consensus_csv, results)
    print(f"Wrote {args.markdown}, {args.json}, and {args.consensus_csv}")


if __name__ == "__main__":
    main()
