import importlib
import logging
import os
import warnings
from pathlib import Path
from typing import Literal

import click
import openai
from dotenv import load_dotenv
from rich import print
from rich.live import Live
from rich.logging import RichHandler

from agentdojo.agent_pipeline.agent_pipeline import DEFENSES, AgentPipeline, PipelineConfig
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
from agentdojo.attacks.attack_registry import ATTACKS, load_attack
from agentdojo.benchmark import SuiteResults, benchmark_suite_with_injections, benchmark_suite_without_injections
from agentdojo.logging import OutputLogger
from agentdojo.models import MODEL_PROVIDERS, ModelsEnum
from agentdojo.probe.delta_probe import (
    benchmark_delta_direct_probe,
    measure_delta_bridge,
    measure_delta_mechanism,
)
from agentdojo.probe.delta_probe import (
    measure_phi_resistance as run_phi_resistance,
)
from agentdojo.probe.phi_embedding import benchmark_phi_abnormality, benchmark_phi_embedding, get_gpt_client
from agentdojo.task_suite.load_suites import get_suite, get_suites
from agentdojo.task_suite.task_suite import TaskSuite


def benchmark_suite(
    suite: TaskSuite,
    model: ModelsEnum,
    logdir: Path,
    force_rerun: bool,
    benchmark_version: str,
    user_tasks: tuple[str, ...] = (),
    injection_tasks: tuple[str, ...] = (),
    model_id: str | None = None,
    attack: str | None = None,
    defense: str | None = None,
    tool_delimiter: str = "tool",
    system_message_name: str | None = None,
    system_message: str | None = None,
    validate_injections: bool = False,
    live: Live | None = None,
    tool_output_format: Literal["yaml", "json"] | None = None,
    measure_delta: str | None = None,
    probe_samples: int = 10,
    delta_direct_probe: bool = False,
    use_probe_template: bool = False,
    measure_phi_embedding: bool = False,
    measure_phi_resistance: bool = False,
    measure_phi_abnormality: bool = False,
    phi_subgoal_model: str | None = None,
    phi_heuristic_subgoal: bool = False,
    delta_bridge_probe: bool = False,
    delta_mechanism_probe: bool = False,
    probe_reasoning: bool = False,
    local_llm_base_url: str | None = None,
    probe_mc_workers: int | None = None,
) -> SuiteResults:
    if not load_dotenv(".env", override=True):
        warnings.warn("No .env file found")

    if local_llm_base_url is not None:
        os.environ["LOCAL_LLM_BASE_URL"] = local_llm_base_url
    if probe_mc_workers is not None:
        if probe_mc_workers < 1:
            raise ValueError("--probe-mc-workers must be >= 1")
        os.environ["AGENTDOJO_PROBE_MC_WORKERS"] = str(probe_mc_workers)

    print(f"Running benchmark for suite: '{suite.name}'")
    print(f"Using model: '{model}'")
    if attack is not None:
        print(f"Using attack: '{attack}'")
    if defense is not None:
        print(f"Using defense: '{defense}'")
    if len(user_tasks) > 0:
        print(f"Using user tasks: {', '.join(user_tasks)}")

    pipeline = AgentPipeline.from_config(
        PipelineConfig(
            llm=model,
            model_id=model_id,
            defense=defense,
            tool_delimiter=tool_delimiter,
            system_message_name=system_message_name,
            system_message=system_message,
            tool_output_format=tool_output_format,
        )
    )

    # Φ abnormality mode: measure clean-context abnormality via A/B/C/D ordinal logprobs
    if measure_phi_abnormality:
        print("[bold cyan]Running Φ abnormality mode[/bold cyan]")
        if phi_subgoal_model is not None:
            print(
                "[yellow]Ignoring --phi-subgoal-model for Φ abnormality; "
                "using the benchmark model/client for logprobs.[/yellow]"
            )

        client = None
        judge_model = model_id or model
        for element in pipeline.elements:
            if isinstance(element, OpenAILLM):
                client = element.client
                judge_model = element.model
                break
            if hasattr(element, "elements"):
                for sub_element in element.elements:
                    if isinstance(sub_element, OpenAILLM):
                        client = sub_element.client
                        judge_model = sub_element.model
                        break
        if client is None:
            client = openai.OpenAI()

        phi_results = benchmark_phi_abnormality(
            suite=suite,
            logdir=logdir,
            force_rerun=force_rerun,
            model=model_id or model,
            client=client,
            judge_model=str(judge_model),
            n_samples=probe_samples,
        )

        print(f"\n[bold]Φ Abnormality Results for suite: '{suite.name}'[/bold]")
        for r in sorted(phi_results, key=lambda x: x.get("phi") if x.get("phi") is not None else 999):
            label = r.get("label", "?")
            template = r.get("template_label", "?")
            phi_val = r.get("phi")
            phi_text = f"{phi_val:.4f}" if phi_val is not None else "N/A"
            probs = r.get("label_probs", {})
            print(
                f"  {label:12s} ({template}): Φ={phi_text}  "
                f"A={probs.get('A', 0):.3f} B={probs.get('B', 0):.3f} "
                f"C={probs.get('C', 0):.3f} D={probs.get('D', 0):.3f}"
            )

        print(f"Finished Φ abnormality for suite: '{suite.name}'")
        return SuiteResults(
            utility_results={},
            security_results={},
            injection_tasks_utility_results={},
        )

    # Φ resistance mode: measure residual execution friction in payload-only context
    if measure_phi_resistance:
        if attack is None:
            raise ValueError("--measure-phi-resistance requires --attack to be specified")

        print("[bold cyan]Running Phi resistance mode[/bold cyan]")

        attacker_ = load_attack(attack, suite, pipeline)

        client = None
        probe_model = model_id or model
        for element in pipeline.elements:
            if isinstance(element, OpenAILLM):
                client = element.client
                probe_model = element.model
                break
            if hasattr(element, "elements"):
                for sub_element in element.elements:
                    if isinstance(sub_element, OpenAILLM):
                        client = sub_element.client
                        probe_model = sub_element.model
                        break
        if client is None:
            client = openai.OpenAI()

        phi_results = run_phi_resistance(
            suite=suite,
            attack=attacker_,
            client=client,
            model=probe_model,
            logdir=logdir,
            test_injection_tasks=injection_tasks if len(injection_tasks) != 0 else None,
            probe_method=measure_delta or "logprobs",
            n_samples=probe_samples,
            force_rerun=force_rerun,
            include_reasoning=probe_reasoning,
        )

        print(f"\n[bold]Phi Resistance Results for suite: '{suite.name}'[/bold]")
        for r in phi_results:
            phi = r.get("phi_resistance")
            phi_text = f"{phi:.3f}" if phi is not None else "N/A"
            payload_key = r.get("payload_key", "?")
            mapped = r.get("mapped_injection_task_ids", [])
            mapped_text = f", mapped={len(mapped)} ITs" if mapped else ""
            print(f"  {payload_key}: Phi_resistance={phi_text} ({mapped_text.lstrip(', ')})")

        print(f"Finished Phi resistance for suite: '{suite.name}'")
        return SuiteResults(
            utility_results={},
            security_results={},
            injection_tasks_utility_results={},
        )

    # Φ embedding mode: measure semantic distance via cosine similarity
    if measure_phi_embedding:
        print("[bold cyan]Running Φ embedding mode[/bold cyan]")

        subgoal_client = None
        subgoal_model = phi_subgoal_model or model_id or model
        if not phi_heuristic_subgoal and str(subgoal_model).startswith("gpt-"):
            subgoal_client = get_gpt_client()
        else:
            for element in pipeline.elements:
                if isinstance(element, OpenAILLM):
                    subgoal_client = element.client
                    subgoal_model = phi_subgoal_model or element.model
                    break
                if hasattr(element, "elements"):
                    for sub_element in element.elements:
                        if isinstance(sub_element, OpenAILLM):
                            subgoal_client = sub_element.client
                            subgoal_model = phi_subgoal_model or sub_element.model
                            break

        phi_results = benchmark_phi_embedding(
            suite=suite,
            logdir=logdir,
            force_rerun=force_rerun,
            model=model_id or model,
            subgoal_client=subgoal_client,
            subgoal_model=str(subgoal_model),
            use_llm_subgoal=not phi_heuristic_subgoal,
        )

        print(f"\n[bold]Φ Embedding Results for suite: '{suite.name}'[/bold]")
        for r in sorted(phi_results, key=lambda x: x.get("phi", 0)):
            label = r.get("label", "?")
            template = r.get("template_label", "?")
            phi_val = r["phi"]
            cos_sim = r["cosine_similarity"]
            subgoal = r.get("subgoal", {}).get("local_subgoal", "")
            print(f"  {label:12s} ({template}): Φ={phi_val:.4f}  cos_sim={cos_sim:.4f}  sq_t={subgoal}")

        print(f"Finished Φ embedding for suite: '{suite.name}'")
        return SuiteResults(
            utility_results={},
            security_results={},
            injection_tasks_utility_results={},
        )

    # Δ_t probe mode: measure legacy direct delta using saved context template.
    # Bridge/mechanism/payload-only modes reuse --measure-delta only as an
    # A/B/C/D scoring method selector, so let their dedicated flags own control.
    if measure_delta is not None and not (delta_bridge_probe or delta_mechanism_probe):
        if attack is None:
            raise ValueError("--measure-delta requires --attack to be specified")

        if not delta_direct_probe:
            raise ValueError(
                "Must use --delta-direct-probe with --measure-delta. "
                "Other delta modes have been removed due to known issues."
            )

        print("[bold cyan]Direct Δ_t probe mode (using saved context template)[/bold cyan]")

        attacker_ = load_attack(attack, suite, pipeline)

        # Find the OpenAI client and model name from the pipeline
        client = None
        probe_model = model_id or model
        for element in pipeline.elements:
            if isinstance(element, OpenAILLM):
                client = element.client
                probe_model = element.model
                break
            if hasattr(element, "elements"):
                for sub_element in element.elements:
                    if isinstance(sub_element, OpenAILLM):
                        client = sub_element.client
                        probe_model = sub_element.model
                        break
        if client is None:
            client = openai.OpenAI()

        delta_results = benchmark_delta_direct_probe(
            suite=suite,
            attack=attacker_,
            client=client,
            model=probe_model,
            logdir=logdir,
            test_injection_tasks=injection_tasks if len(injection_tasks) != 0 else None,
            probe_method=measure_delta,
            n_samples=probe_samples,
            force_rerun=force_rerun,
        )

        for r in delta_results:
            if r.delta_t is not None:
                status = f"Δ_t={r.delta_t:.3f}"
            elif not r.injection_triggered:
                status = "not triggered"
            else:
                status = "unavailable"
            method_info = f" [{r.probe_method}]" if r.probe_method != "logprobs" else ""
            samples_info = f" (n={r.n_samples})" if r.n_samples else ""
            print(
                f"  {r.injection_task_id}: {status}{method_info}{samples_info} (p_yes={r.p_yes:.3f}, p_no={r.p_no:.3f})"
            )

        print(f"Finished Δ_t probe for suite: '{suite.name}'")
        return SuiteResults(
            utility_results={},
            security_results={},
            injection_tasks_utility_results={},
        )

    # Δ_bridge probe mode: measure full-injection execution induction
    if delta_bridge_probe:
        if attack is None:
            raise ValueError("--delta-bridge-probe requires --attack to be specified")

        print("[bold cyan]Δ_bridge probe mode (full-injection execution induction)[/bold cyan]")

        attacker_ = load_attack(attack, suite, pipeline)

        # Find the OpenAI client and model name from the pipeline
        client = None
        probe_model = model_id or model
        for element in pipeline.elements:
            if isinstance(element, OpenAILLM):
                client = element.client
                probe_model = element.model
                break
            if hasattr(element, "elements"):
                for sub_element in element.elements:
                    if isinstance(sub_element, OpenAILLM):
                        client = sub_element.client
                        probe_model = sub_element.model
                        break
        if client is None:
            client = openai.OpenAI()

        bridge_results = measure_delta_bridge(
            suite=suite,
            attack=attacker_,
            client=client,
            model=probe_model,
            logdir=logdir,
            test_injection_tasks=injection_tasks if len(injection_tasks) != 0 else None,
            probe_method=measure_delta or "logprobs",
            n_samples=probe_samples,
            force_rerun=force_rerun,
        )

        for r in bridge_results:
            if r.delta_bridge is not None:
                status = f"Δ_bridge={r.delta_bridge:.3f}"
            else:
                status = "unavailable"
            full_score = f"{r.full_injection_score:.3f}" if r.full_injection_score is not None else "N/A"
            payload_score = f"{r.payload_only_score:.3f}" if r.payload_only_score is not None else "N/A"
            prefix_gain = f"{r.prefix_gain_signed:.3f}" if r.prefix_gain_signed is not None else "N/A"
            print(
                f"  {r.injection_task_id}: {status} "
                f"(S_full={full_score}, S_payload={payload_score}, prefix_gain={prefix_gain})"
            )

        print(f"Finished Δ_bridge probe for suite: '{suite.name}'")
        return SuiteResults(
            utility_results={},
            security_results={},
            injection_tasks_utility_results={},
        )

    # Δ mechanism probe mode: measure prefix-to-payload mechanism bridge
    if delta_mechanism_probe:
        if attack is None:
            raise ValueError("--delta-mechanism-probe requires --attack to be specified")

        print("[bold cyan]Δ_mechanism probe mode (prefix-to-payload mechanism bridge)[/bold cyan]")

        attacker_ = load_attack(attack, suite, pipeline)

        client = None
        probe_model = model_id or model
        for element in pipeline.elements:
            if isinstance(element, OpenAILLM):
                client = element.client
                probe_model = element.model
                break
            if hasattr(element, "elements"):
                for sub_element in element.elements:
                    if isinstance(sub_element, OpenAILLM):
                        client = sub_element.client
                        probe_model = sub_element.model
                        break
        if client is None:
            client = openai.OpenAI()

        mechanism_results = measure_delta_mechanism(
            suite=suite,
            attack=attacker_,
            client=client,
            model=probe_model,
            logdir=logdir,
            test_injection_tasks=injection_tasks if len(injection_tasks) != 0 else None,
            probe_method=measure_delta or "logprobs",
            n_samples=probe_samples,
            force_rerun=force_rerun,
            include_reasoning=probe_reasoning,
        )

        for r in mechanism_results:
            delta = r.get("delta_mechanism")
            test = r.get("test_score")
            delta_text = f"{delta:.3f}" if delta is not None else "N/A"
            test_text = f"{test:.3f}" if test is not None else "N/A"
            print(
                f"  {r['injection_task_id']}: Δ_mech={delta_text} "
                f"(S_test={test_text})"
            )

        print(f"Finished Δ_mechanism probe for suite: '{suite.name}'")
        return SuiteResults(
            utility_results={},
            security_results={},
            injection_tasks_utility_results={},
        )

    # Normal benchmark mode (with optional --use-probe-template for ASR)
    with OutputLogger(str(logdir), live=live):
        if attack is None:
            results = benchmark_suite_without_injections(
                pipeline,
                suite,
                user_tasks=user_tasks if len(user_tasks) != 0 else None,
                logdir=logdir,
                force_rerun=force_rerun,
                benchmark_version=benchmark_version,
            )
        else:
            attacker_ = load_attack(attack, suite, pipeline)

            # Resolve probe template path if --use-probe-template
            probe_template_path = None
            if use_probe_template:
                probe_model = model_id or model
                # OpenRouter: 模板路径用扁平注册名，与 from_config 的 ASR 结果目录一致
                # (model_id 含发布者前缀如 z-ai/glm-4.7-flash，否则会落到 z-ai_glm-4.7-flash/)
                if MODEL_PROVIDERS.get(ModelsEnum(model)) == "openrouter":
                    probe_model = model
                pipeline_name = str(probe_model).replace("/", "_")
                candidate = logdir / pipeline_name / suite.name / "probe_template.json"
                if candidate.exists():
                    probe_template_path = candidate
                else:
                    raise FileNotFoundError(
                        "probe_template.json not found. "
                        "Collect a template first: run IT0, then use _extract_template_from_trajectory."
                    )
                print(f"[bold cyan]Using probe template: {probe_template_path}[/bold cyan]")

            results = benchmark_suite_with_injections(
                pipeline,
                suite,
                attacker_,
                user_tasks=user_tasks if len(user_tasks) != 0 else None,
                injection_tasks=injection_tasks if len(injection_tasks) != 0 else None,
                validate_injections=validate_injections,
                logdir=logdir,
                force_rerun=force_rerun,
                benchmark_version=benchmark_version,
                probe_template_path=probe_template_path,
            )
    print(f"Finished benchmark for suite: '{suite.name}'")

    return results


def show_results(suite_name: str, results: SuiteResults, show_security_results: bool):
    utility_results = list(results["utility_results"].values())
    if len(utility_results) == 0:
        return

    avg_utility = sum(utility_results) / len(utility_results)
    print(f"Results for suite {suite_name}")
    print(f"Average utility: {avg_utility * 100:.2f}%")

    if show_security_results:
        passed_injection_tasks = sum(v for v in results["injection_tasks_utility_results"].values() if v is not None)
        total_injection_tasks = len(results["injection_tasks_utility_results"])
        print(f"\nPassed injection tasks as user tasks: {passed_injection_tasks}/{total_injection_tasks}")

        security_results = [v for v in results["security_results"].values() if v is not None]
        if security_results:
            avg_security = sum(security_results) / len(security_results)
            print(
                f"Average security: {avg_security * 100:.2f}% (excluding {len(results['security_results']) - len(security_results)} None)"
            )
        else:
            print("Average security: N/A (all None)")


@click.command()
@click.option(
    "--model",
    default="gpt-4o-2024-05-13",
    type=click.Choice([value for value in ModelsEnum]),
    help="The language model to benchmark. Defaults to `gpt-4o-2024-05-13`.",
)
@click.option(
    "--model-id",
    type=str,
    default=None,
    help="The model id for local models.",
)
@click.option(
    "--benchmark-version",
    default="v1.2.2",
    type=str,
    help="The version of the benchmark to run. Defaults to `v1.2.2`.",
)
@click.option(
    "--tool-delimiter",
    type=str,
    default="tool",
    help="Which tool delimiter to use. Used for local models only.",
)
@click.option(
    "--logdir",
    default="./runs",
    type=Path,
    help="The directory to save logs. Defaults to `./runs`.",
)
@click.option(
    "--attack",
    type=str,
    default=None,
    help=f"The attack to use. `None` by default. It should be one of {ATTACKS}, or a custom attack defined and registered in of of the `--module-to-load`. If `None`, no attack is used.",
)
@click.option(
    "--defense",
    type=click.Choice(DEFENSES),
    default=None,
    help="The defense to use. `None` by default.",
)
@click.option(
    "--system-message-name",
    type=str,
    default=None,
    help="The name of the system message to use among the default ones in `data/system_messages.yaml`.",
)
@click.option(
    "--system-message",
    type=str,
    default=None,
    help="The system message to use (as a string). If provided, `--system-message-name` is ignored.",
)
@click.option(
    "--user-task",
    "-ut",
    "user_tasks",
    type=str,
    multiple=True,
    default=tuple(),
    help="The user tasks to benchmark. If not provided, all tasks in the suite are run.",
)
@click.option(
    "--injection-task",
    "-it",
    "injection_tasks",
    type=str,
    multiple=True,
    default=tuple(),
    help="The injection tasks to benchmark. If not provided, all tasks in the suite are run.",
)
@click.option(
    "--suite",
    "-s",
    "suites",
    type=str,
    multiple=True,
    default=tuple(),
    help="The suites to benchmark. If not provided, all suites are run.",
)
@click.option(
    "--max-workers",
    type=int,
    default=1,
    help="How many suites can be benchmarked in parallel through multithreading. Nothing is parallelized by default.",
)
@click.option(
    "--force-rerun",
    "-f",
    is_flag=True,
    help="Whether to re-run tasks that have already been run.",
)
@click.option(
    "--module-to-load",
    "-ml",
    "modules_to_load",
    type=str,
    multiple=True,
    default=tuple(),
    help="The modules to load before running the benchmark. Useful for registering custom attacks, defenses, or suites.",
)
@click.option(
    "--validate-injections",
    is_flag=True,
    default=False,
    help="Run each injection task as a user task first to validate that the injection text is executable.",
)
@click.option(
    "--measure-delta",
    type=click.Choice(["logprobs", "monte_carlo"]),
    default=None,
    help="A/B/C/D probe scoring method. By itself, runs legacy Δ_t and requires --delta-direct-probe.",
)
@click.option(
    "--probe-samples",
    default=10,
    type=int,
    help="Number of Monte Carlo samples for Δ_t probe when logprobs are unavailable (default: 10).",
)
@click.option(
    "--delta-direct-probe",
    is_flag=True,
    default=False,
    help="Direct Δ_t probe: use saved context template. Requires --measure-delta.",
)
@click.option(
    "--use-probe-template",
    is_flag=True,
    default=False,
    help="Use saved probe template as initial context for normal benchmark. "
    "Ensures ASR is measured under the same context as Δ_t. "
    "Requires --attack.",
)
@click.option(
    "--measure-phi-embedding",
    is_flag=True,
    default=False,
    help="Measure Φ via embedding cosine similarity (payload vs sq_t semantic distance).",
)
@click.option(
    "--measure-phi-abnormality",
    is_flag=True,
    default=False,
    help="Measure Φ via clean-context A/B/C/D abnormality logprobs over candidate payloads.",
)
@click.option(
    "--measure-phi-resistance",
    is_flag=True,
    default=False,
    help="Measure payload-level residual Phi resistance under payload-only workflow context.",
)
@click.option(
    "--phi-subgoal-model",
    default=None,
    help="Chat model used to extract sq_t from the clean probe template. Defaults to the benchmark model.",
)
@click.option(
    "--phi-heuristic-subgoal",
    is_flag=True,
    default=False,
    help="Use a deterministic heuristic sq_t extractor instead of an LLM.",
)
@click.option(
    "--delta-bridge-probe",
    is_flag=True,
    default=False,
    help="Measure Δ_bridge: full-injection execution induction, with payload-only diagnostics.",
)
@click.option(
    "--delta-mechanism-probe",
    is_flag=True,
    default=False,
    help="Measure mechanism Δ as the prefix contribution to the target payload.",
)
@click.option(
    "--probe-reasoning",
    is_flag=True,
    default=False,
    help="Add separate diagnostic reasoning calls to Phi/Delta probe outputs without changing probe scores.",
)
@click.option(
    "--local-llm-base-url",
    default=None,
    help="OpenAI-compatible local LLM endpoint, e.g. http://GPU6:8000/v1. Overrides LOCAL_LLM_BASE_URL.",
)
@click.option(
    "--probe-mc-workers",
    default=None,
    type=int,
    help="Internal Monte Carlo probe concurrency. Overrides AGENTDOJO_PROBE_MC_WORKERS.",
)
def main(
    suites: tuple[str, ...],
    model: ModelsEnum,
    benchmark_version: str = "v1.2.2",
    logdir: Path = Path("./runs"),
    user_tasks: tuple[str, ...] = (),
    injection_tasks: tuple[str, ...] = (),
    model_id: str | None = None,
    attack: str | None = None,
    defense: str | None = None,
    tool_delimiter: str = "tool",
    system_message_name: str | None = None,
    system_message: str | None = None,
    max_workers: int = 1,
    force_rerun: bool = False,
    modules_to_load: tuple[str, ...] = (),
    validate_injections: bool = False,
    measure_delta: str | None = None,
    probe_samples: int = 10,
    delta_direct_probe: bool = False,
    use_probe_template: bool = False,
    measure_phi_embedding: bool = False,
    measure_phi_resistance: bool = False,
    measure_phi_abnormality: bool = False,
    phi_subgoal_model: str | None = None,
    phi_heuristic_subgoal: bool = False,
    delta_bridge_probe: bool = False,
    delta_mechanism_probe: bool = False,
    probe_reasoning: bool = False,
    local_llm_base_url: str | None = None,
    probe_mc_workers: int | None = None,
):
    for module in modules_to_load:
        importlib.import_module(module)

    if len(suites) == 0:
        suites = tuple(get_suites(benchmark_version).keys())

    if len(suites) != 1:
        print(f"Benchmarking suites {', '.join(suites)}")

    if len(suites) != 1 and len(user_tasks) != 0:
        raise ValueError("A user task can be specified only when one suite is being executed")

    results = {}
    for suite_name in suites:
        suite = get_suite(benchmark_version, suite_name)
        results[suite_name] = benchmark_suite(
            suite,
            model,
            logdir,
            benchmark_version=benchmark_version,
            user_tasks=user_tasks,
            injection_tasks=injection_tasks,
            model_id=model_id,
            attack=attack,
            defense=defense,
            tool_delimiter=tool_delimiter,
            system_message_name=system_message_name,
            system_message=system_message,
            force_rerun=force_rerun,
            validate_injections=validate_injections,
            measure_delta=measure_delta,
            probe_samples=probe_samples,
            delta_direct_probe=delta_direct_probe,
            use_probe_template=use_probe_template,
            measure_phi_embedding=measure_phi_embedding,
            measure_phi_resistance=measure_phi_resistance,
            measure_phi_abnormality=measure_phi_abnormality,
            phi_subgoal_model=phi_subgoal_model,
            phi_heuristic_subgoal=phi_heuristic_subgoal,
            delta_bridge_probe=delta_bridge_probe,
            delta_mechanism_probe=delta_mechanism_probe,
            probe_reasoning=probe_reasoning,
            local_llm_base_url=local_llm_base_url,
            probe_mc_workers=probe_mc_workers,
        )
    combined_results = SuiteResults(utility_results={}, security_results={}, injection_tasks_utility_results={})
    for suite_name, result in results.items():
        show_results(suite_name, result, attack is not None)
        for user_task, injection_task in result["utility_results"]:
            new_user_task = suite_name + "_" + user_task
            combined_results["utility_results"][(new_user_task, injection_task)] = result["utility_results"][
                (user_task, injection_task)
            ]
        for user_task, injection_task in result["security_results"]:
            new_user_task = suite_name + "_" + user_task
            combined_results["security_results"][(new_user_task, injection_task)] = result["security_results"][
                (user_task, injection_task)
            ]
        for injection_task in result["injection_tasks_utility_results"]:
            new_injection_task = suite_name + "_" + injection_task
            combined_results["injection_tasks_utility_results"][new_injection_task] = result[
                "injection_tasks_utility_results"
            ][injection_task]
    show_results("combined", combined_results, attack is not None)


if __name__ == "__main__":
    format = "%(message)s"
    logging.basicConfig(
        format=format,
        level=logging.INFO,
        datefmt="%H:%M:%S",
        handlers=[RichHandler(show_path=False, markup=True)],
    )
    main()
