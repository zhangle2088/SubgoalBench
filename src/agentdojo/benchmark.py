import copy
import json
import logging
import warnings
from collections.abc import Sequence
from json import JSONDecodeError
from pathlib import Path
from typing import cast

from cohere.core.api_error import ApiError
from google.genai.errors import ServerError
from openai import BadRequestError, UnprocessableEntityError
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator
from typing_extensions import Self, TypedDict

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
from agentdojo.agent_pipeline.pi_detector import PromptInjectionDetector
from agentdojo.attacks.base_attacks import BaseAttack
from agentdojo.base_tasks import BaseInjectionTask, BaseUserTask
from agentdojo.functions_runtime import Env
from agentdojo.logging import Logger, TraceLogger
from agentdojo.probe.delta_probe import _reconstruct_chat_messages
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.task_suite.task_suite import TaskSuite
from agentdojo.types import ChatMessage, MessageContentBlock, get_text_content_as_str, text_content_block_from_string


def _find_probe_template_source_task(template_data: dict, suite: TaskSuite) -> BaseInjectionTask:
    source_it_id = template_data.get("source_injection_task_id")
    source_prefix = template_data.get("source_prefix")

    if source_it_id is not None:
        source_task = suite.get_injection_task_by_id(source_it_id)
        if source_task.PLAIN_INJECTION_PREFIX != source_prefix:
            raise ValueError(
                "probe_template.json is stale: source_injection_task_id "
                f"{source_it_id!r} now has a different PLAIN_INJECTION_PREFIX. "
                "Regenerate the probe template from the current suite code."
            )
        return source_task

    matching_tasks = [
        it for it in suite.injection_tasks.values() if it.PLAIN_INJECTION_PREFIX == source_prefix
    ]
    if len(matching_tasks) == 1:
        return matching_tasks[0]
    if len(matching_tasks) > 1:
        raise ValueError(
            "probe_template.json is ambiguous: source_prefix matches multiple injection tasks exactly. "
            "Regenerate the probe template so it includes source_injection_task_id."
        )

    prefix_preview = repr(source_prefix[:80] if isinstance(source_prefix, str) else source_prefix)
    raise ValueError(
        "probe_template.json is stale or incomplete: source_prefix does not exactly match any current "
        f"injection task prefix ({prefix_preview}). Regenerate the probe template from the current suite code."
    )


def _replace_probe_template_source_text(context: list[dict], source_prefix: str, target_text: str) -> int:
    replacements = 0
    trigger_index = -1
    for index, msg in enumerate(context):
        if msg.get("role") == "tool" and msg.get("content"):
            if isinstance(msg["content"], str) and source_prefix in msg["content"]:
                msg["content"] = msg["content"].replace(source_prefix, target_text, 1)
                replacements += 1
                trigger_index = index
    if replacements != 1:
        raise ValueError(
            "probe_template.json is invalid for fixed-context ASR: expected source_prefix to occur in exactly "
            f"one tool message, found {replacements}. Regenerate the probe template."
        )
    return trigger_index


def _pipeline_elements(agent_pipeline: BasePipelineElement) -> list[BasePipelineElement]:
    if isinstance(agent_pipeline, AgentPipeline):
        return list(agent_pipeline.elements)
    elements = getattr(agent_pipeline, "elements", None)
    if elements is None:
        return []
    return list(elements)


def _iter_pipeline_elements(agent_pipeline: BasePipelineElement):
    for element in _pipeline_elements(agent_pipeline):
        yield element
        yield from _iter_pipeline_elements(element)


def _pipeline_name_has_defense(agent_pipeline: BasePipelineElement, defense: str) -> bool:
    pipeline_name = getattr(agent_pipeline, "name", None)
    return isinstance(pipeline_name, str) and (
        pipeline_name == defense or pipeline_name.endswith(f"-{defense}")
    )


def _is_spotlighting_pipeline(agent_pipeline: BasePipelineElement) -> bool:
    if _pipeline_name_has_defense(agent_pipeline, "spotlighting_with_delimiting"):
        return True
    elements = _pipeline_elements(agent_pipeline)
    if not elements or not isinstance(elements[0], SystemMessage):
        return False
    return "<< before them and the symbol >> after them" in elements[0].system_message


def _is_repeat_user_prompt_pipeline(agent_pipeline: BasePipelineElement) -> bool:
    if _pipeline_name_has_defense(agent_pipeline, "repeat_user_prompt"):
        return True
    for element in _pipeline_elements(agent_pipeline)[2:]:
        nested_elements = getattr(element, "elements", None)
        if nested_elements is not None and any(isinstance(nested, InitQuery) for nested in nested_elements):
            return True
    return False


def _find_prompt_injection_detector(agent_pipeline: BasePipelineElement) -> PromptInjectionDetector | None:
    for element in _iter_pipeline_elements(agent_pipeline):
        if isinstance(element, PromptInjectionDetector):
            return element
    return None


def _replace_message_text(message: ChatMessage, text: str) -> None:
    if message.get("content") is None:
        return
    message["content"] = [cast(MessageContentBlock, text_content_block_from_string(text))]


def _tool_output_text(message: ChatMessage) -> str:
    content = message.get("content")
    if content is None:
        return ""
    return get_text_content_as_str(content)


def _is_delimited_tool_output(text: str) -> bool:
    return text.startswith("<<") and text.endswith(">>")


def _user_prompt_already_present(message: ChatMessage, user_prompt: str) -> bool:
    return message["role"] == "user" and _tool_output_text(message) == user_prompt


def _normalize_probe_template_initial_messages(
    agent_pipeline: BasePipelineElement,
    messages: Sequence[ChatMessage],
    trigger_index: int,
    user_prompt: str,
) -> list[ChatMessage]:
    normalized_messages = copy.deepcopy(list(messages))

    elements = _pipeline_elements(agent_pipeline)
    if elements and isinstance(elements[0], SystemMessage):
        system_message = elements[0].system_message
        if normalized_messages and normalized_messages[0]["role"] == "system":
            _replace_message_text(normalized_messages[0], system_message)

    if _is_spotlighting_pipeline(agent_pipeline):
        for message in normalized_messages:
            if message["role"] == "tool":
                tool_output = _tool_output_text(message)
                if not _is_delimited_tool_output(tool_output):
                    _replace_message_text(message, f"<<{tool_output}>>")

    detector = _find_prompt_injection_detector(agent_pipeline)
    if detector is not None and 0 <= trigger_index < len(normalized_messages):
        message = normalized_messages[trigger_index]
        if message["role"] == "tool":
            if detector.mode == "message":
                text = _tool_output_text(message)
            elif detector.mode == "full_conversation":
                text = "\n".join(
                    [
                        f"{m['role']}: {_tool_output_text(m)}"
                        for m in normalized_messages[: trigger_index + 1]
                        if m.get("content") is not None
                    ]
                )
            else:
                raise ValueError(
                    f"Invalid checking mode: {detector.mode} (valid options are 'message' and 'full_conversation')"
                )

            detection_result = detector.detect(text)
            is_injection = detection_result if not isinstance(detection_result, tuple) else detection_result[0]
            if is_injection:
                message["content"] = detector.transform(message["content"] or [])

    if _is_repeat_user_prompt_pipeline(agent_pipeline):
        repeated_messages: list[ChatMessage] = []
        for index, message in enumerate(normalized_messages):
            repeated_messages.append(message)
            next_message = normalized_messages[index + 1] if index + 1 < len(normalized_messages) else None
            is_end_of_tool_block = message["role"] == "tool" and (next_message is None or next_message["role"] != "tool")
            if is_end_of_tool_block and (
                next_message is None or not _user_prompt_already_present(next_message, user_prompt)
            ):
                repeated_messages.append(
                    {
                        "role": "user",
                        "content": [cast(MessageContentBlock, text_content_block_from_string(user_prompt))],
                    }
                )
        normalized_messages = repeated_messages

    return normalized_messages


class SuiteResults(TypedDict):
    """The results of running a suite of tasks with a given pipeline."""

    utility_results: dict[tuple[str, str], float]
    """The utility results for each injection task and user task couple. The
    key is a tuple of the user task ID and the injection task ID."""
    security_results: dict[tuple[str, str], float | None]
    """The security results for each injection task and user task couple. The
    key is a tuple of the user task ID and the injection task ID."""
    injection_tasks_utility_results: dict[str, float]
    """The utility results for each injection task. The key is the injection task ID."""


def aggregate_results(results: list[dict[tuple[str, str], float]]) -> float:
    all_results = [result for results in results for result in results.values()]
    return sum(all_results) / len(all_results)


def run_task_with_injection_tasks(
    suite: TaskSuite,
    agent_pipeline: BasePipelineElement,
    user_task: BaseUserTask,
    attack: BaseAttack,
    logdir: Path | None,
    force_rerun: bool,
    injection_tasks: Sequence[str] | None = None,
    benchmark_version: str | None = None,
    probe_template_path: Path | None = None,
) -> tuple[dict[tuple[str, str], float], dict[tuple[str, str], float | None]]:
    """Runs the given user task with the given injection tasks (or all tasks if no injection
    task is provided) by injecting the environment by using the given attack.

    Args:
        suite: The task suite to run.
        agent_pipeline: The agent pipeline to use.
        user_task: The user task to run.
        attack: The attack to run.
        logdir: The directory to save logs to.
        force_rerun: Whether to force rerun the task in case in the logdir there already exists
            a log for the task.
        injection_tasks: The injection tasks to run. If None, all injection tasks in the suite will be run.

    Returns:
        A tuple of two dictionaries. The first dictionary contains the utility results for each injection
            task and user task couple. The second dictionary contains the security results for each
            injection and user task couple.

    """
    utility_results: dict[tuple[str, str], float] = {}
    security_results: dict[tuple[str, str], float | None] = {}

    if attack.is_dos_attack:
        # No need to run all injection tasks since we don't care about the injection target!
        injection_tasks_to_run = [next(iter(suite.injection_tasks.keys()))]
    else:
        injection_tasks_to_run = suite.injection_tasks

    if injection_tasks is not None and not attack.is_dos_attack:
        injection_tasks_to_run = injection_tasks

    # Load probe template if provided
    template_data = None
    source_injection_task = None
    if probe_template_path is not None:
        with probe_template_path.open() as f:
            template_data = json.load(f)
        source_injection_task = _find_probe_template_source_task(template_data, suite)

    for injection_task_id in injection_tasks_to_run:
        injection_task = suite.get_injection_task_by_id(injection_task_id)
        task_injections = attack.attack(user_task, injection_task)

        if logdir is not None and agent_pipeline.name is not None:
            try:
                task_result = load_task_results(
                    agent_pipeline.name.replace("/", "_"),
                    suite.name,
                    user_task.ID,
                    attack_name=attack.name,
                    injection_task=injection_task.ID,
                    logdir=logdir,
                )
            except (ValidationError, FileNotFoundError):
                task_result = None
        else:
            task_result = None

        if task_result is not None and not force_rerun:
            logging.info(f"Skipping task '{user_task.ID}' with '{injection_task.ID}' because it was already run.")
            utility, security = task_result.utility, task_result.security
        else:
            # a trace logger captures logs and saves them, but also passes them to the delegate logger
            with TraceLogger(
                delegate=Logger.get(),
                suite_name=suite.name,
                user_task_id=user_task.ID,
                injection_task_id=injection_task_id,
                injections=task_injections,
                attack_type=attack.name,
                pipeline_name=agent_pipeline.name,
                benchmark_version=benchmark_version,
            ) as logger:
                try:
                    # Build initial_messages from probe template if available
                    initial_messages = None
                    if template_data is not None and source_injection_task is not None:
                        context = copy.deepcopy(template_data["context_messages"])
                        source_prefix = source_injection_task.PLAIN_INJECTION_PREFIX
                        target_text = injection_task.PLAIN_INJECTION_TEXT
                        if source_prefix is None or target_text is None:
                            raise ValueError(
                                "Cannot use probe template with an injection task missing PLAIN_INJECTION_PREFIX "
                                "or PLAIN_INJECTION_TEXT."
                            )
                        trigger_index = _replace_probe_template_source_text(context, source_prefix, target_text)
                        initial_messages = _reconstruct_chat_messages(context)
                        initial_messages = _normalize_probe_template_initial_messages(
                            agent_pipeline,
                            initial_messages,
                            trigger_index,
                            user_task.PROMPT,
                        )

                    utility, security = suite.run_task_with_pipeline(
                        agent_pipeline,
                        user_task,
                        injection_task,
                        task_injections,
                        initial_messages=initial_messages,
                    )
                except BadRequestError as e:
                    if (
                        e.code == "context_length_exceeded"
                        or e.param == "max_tokens"
                        or "reduce the length of the messages." in repr(e)
                        or "repetitive tool calls" in repr(e).lower()
                    ):
                        logger.log_error(
                            f"Skipping task '{user_task.ID}' with '{injection_task.ID}' due to bad request (skipped): {e}"
                        )
                        utility = 0.0
                        security = 0.0
                    else:
                        raise e
                except ApiError as e:
                    if "internal server error" in str(e):
                        logger.log_error(
                            f"Skipping task '{user_task.ID}' with '{injection_task.ID}' because of internal server error: {e}"
                        )
                        utility = 0.0
                        security = 0.0
                    else:
                        raise e
                except ServerError as e:
                    logger.log_error(
                        f"Skipping task '{user_task.ID}' with '{injection_task.ID}' because of internal server error: {e}"
                    )
                    utility = 0.0
                    security = 0.0
                except JSONDecodeError as e:
                    logger.log_error(
                        f"Skipping task {user_task.ID} with '{injection_task.ID}' because of JSON decode error: {e}"
                    )
                    utility = 0.0
                    security = 0.0

                if attack.is_dos_attack:
                    # DOS success = task failure = unsafe; task success = DOS failure = safe.
                    security = 1.0 if utility > 0 else 0.0

            logger.set_contextarg("utility", utility)
            logger.set_contextarg("security", security)

        utility_results[(user_task.ID, injection_task_id)] = utility
        security_results[(user_task.ID, injection_task_id)] = security
    return utility_results, security_results


def benchmark_suite_with_injections(
    agent_pipeline: BasePipelineElement,
    suite: TaskSuite[Env],
    attack: BaseAttack,
    logdir: Path | None,
    force_rerun: bool,
    user_tasks: Sequence[str] | None = None,
    injection_tasks: Sequence[str] | None = None,
    validate_injections: bool = False,
    verbose: bool = True,
    benchmark_version: str | None = None,
    probe_template_path: Path | None = None,
) -> SuiteResults:
    """Benchmark a suite with injections.

    Args:
        agent_pipeline: The agent pipeline to use.
        suite: The suite to benchmark.\
        attack: The attack to use.
        logdir: The directory to save logs to.
        force_rerun: Whether to force rerun the task in case in the logdir there already exists
            a log for the task.
        user_tasks: A subset of user tasks to run. If None, all user tasks are run.
        injection_tasks: A subset of injection tasks to run. If None, all injection tasks are run.
        verbose: Whether to print the results.
    """
    suite_utility_results: dict[tuple[str, str], float] = {}
    suite_security_results: dict[tuple[str, str], float | None] = {}

    if user_tasks is not None:
        user_tasks_to_run = [suite.get_user_task_by_id(user_task_id) for user_task_id in user_tasks]
    else:
        user_tasks_to_run = suite.user_tasks.values()

    if injection_tasks is not None:
        injection_tasks_to_run = {
            injection_task_id: suite.get_injection_task_by_id(injection_task_id)
            for injection_task_id in injection_tasks
        }
    else:
        injection_tasks_to_run = suite.injection_tasks

    injection_tasks_utility_results = {}
    if validate_injections and not attack.is_dos_attack:
        for injection_task_id, injection_task in injection_tasks_to_run.items():
            successful, _ = run_task_without_injection_tasks(
                suite, agent_pipeline, injection_task, logdir, force_rerun, benchmark_version
            )
            injection_tasks_utility_results[injection_task_id] = successful

        if not all(injection_tasks_utility_results.values()):
            failed = [k for k, v in injection_tasks_utility_results.items() if not v]
            warnings.warn(f"Injection tasks {failed} were not solved as user tasks (injection validation failed).")

    for user_task in user_tasks_to_run:
        utility, security = run_task_with_injection_tasks(
            suite,
            agent_pipeline,
            user_task,
            attack,
            logdir,
            force_rerun,
            injection_tasks,
            benchmark_version,
            probe_template_path=probe_template_path,
        )
        suite_utility_results.update(utility)
        suite_security_results.update(security)

    return SuiteResults(
        utility_results=suite_utility_results,
        security_results=suite_security_results,
        injection_tasks_utility_results=injection_tasks_utility_results,
    )


def run_task_without_injection_tasks(
    suite: TaskSuite,
    agent_pipeline: BasePipelineElement,
    task: BaseUserTask | BaseInjectionTask,
    logdir: Path | None,
    force_rerun: bool,
    benchmark_version: str | None = None,
) -> tuple[float, float | None]:
    """Run a task without injections. Useful to benchmark the utility of a pipeline.

    Args:
        suite: The suite to use to run the benchmark.
        agent_pipeline: The agent pipeline to benchmark.
        task: The task to run.
        logdir: The directory to save logs to.
        force_rerun: Whether to force rerun the task in case in the logdir there already exists
            a log for the task.

    Returns:
        A tuple with the utility and security of the task. The security is always True.
    """
    if logdir is not None and agent_pipeline.name is not None:
        result_path = logdir / agent_pipeline.name.replace("/", "_") / suite.name / task.ID / "none" / "none.json"
        if result_path.exists() and not force_rerun:
            logging.info(f"Skipping task '{task.ID}' with no injections because it was already run.")
            try:
                task_result = load_task_results(
                    agent_pipeline.name.replace("/", "_"),
                    suite.name,
                    task.ID,
                    attack_name="none",
                    injection_task="none",
                    logdir=logdir,
                )
                return task_result.utility, task_result.security
            except Exception:
                return 1.0, 1.0
    else:
        pass

    with TraceLogger(
        delegate=Logger.get(),
        suite_name=suite.name,
        user_task_id=task.ID,
        injection_task_id=None,
        injections={},
        attack_type="none",
        pipeline_name=agent_pipeline.name,
        benchmark_version=benchmark_version,
    ) as logger:
        try:
            utility, security = suite.run_task_with_pipeline(agent_pipeline, task, injection_task=None, injections={})
        except BadRequestError as e:
            if (
                e.code == "context_length_exceeded"
                or e.param == "max_tokens"
                or "reduce the length of the messages." in repr(e)
            ):
                logger.log_error(f"Skipping task {task.ID} due to context_length_exceeded: {e}")
                utility = 0.0
                security = 1.0
            else:
                raise e
        except UnprocessableEntityError as e:
            if "max_new_tokens" in str(e):
                logger.log_error(f"Skipping task {task.ID} due to context_length_exceeded: {e}")
                utility = 0.0
                security = 1.0
            else:
                raise e
        except ApiError as e:
            if "internal server error" in str(e):
                logger.log_error(f"Skipping task {task.ID} because of internal server error: {e}")
                utility = 0.0
                security = 1.0
            else:
                raise e
        except ServerError as e:
            logger.log_error(f"Skipping task {task.ID} because of internal server error: {e}")
            utility = 0.0
            security = 1.0
        except JSONDecodeError as e:
            logger.log_error(f"Skipping task {task.ID} because of JSON decode error: {e}")
            utility = 0.0
            security = 1.0
        logger.set_contextarg("utility", utility)
        logger.set_contextarg("security", security)

    return utility, security


def benchmark_suite_without_injections(
    agent_pipeline: BasePipelineElement,
    suite: TaskSuite,
    logdir: Path | None,
    force_rerun: bool,
    user_tasks: Sequence[str] | None = None,
    benchmark_version: str | None = None,
) -> SuiteResults:
    """Benchmark a suite without injections.

    Args:
        agent_pipeline: The agent pipeline to use.
        suite: The suite to benchmark.\
        attack: The attack to use.
        logdir: The directory to save logs to.
        force_rerun: Whether to force rerun the task in case in the logdir there already exists
            a log for the task.
        user_tasks: A subset of user tasks to run. If None, all user tasks are run.
    """

    suite_utility_results: dict[tuple[str, str], float] = {}
    suite_security_results: dict[tuple[str, str], float | None] = {}

    if user_tasks is not None:
        user_tasks_to_run = [suite.get_user_task_by_id(user_task_id) for user_task_id in user_tasks]
    else:
        user_tasks_to_run = suite.user_tasks.values()

    for user_task in user_tasks_to_run:
        utility, security = run_task_without_injection_tasks(
            suite, agent_pipeline, user_task, logdir, force_rerun, benchmark_version
        )
        suite_utility_results[(user_task.ID, "")] = utility
        suite_security_results[(user_task.ID, "")] = security

    return SuiteResults(
        utility_results=suite_utility_results,
        security_results=suite_security_results,
        injection_tasks_utility_results={},
    )


class TaskResults(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    suite_name: str
    pipeline_name: str
    user_task_id: str
    injection_task_id: str | None
    attack_type: str | None
    injections: dict[str, str]
    messages: list[ChatMessage]
    error: str | None
    utility: float
    security: float | None
    duration: float = 0.0

    @model_validator(mode="after")
    def check_messages(self) -> Self:
        if len(self.messages) < 2 and "claude-3-opus" not in self.pipeline_name:
            raise ValueError("TaskResults must have at least two messages.")
        return self


def convert_old_messages_format(messages: list[dict]) -> list[dict]:
    """Convert messages from old format (string content) to new format (content blocks).

    The new format was introduced with commit d67f9d141305e599ca2056f430f703d4021fd82a.
    """
    converted_messages = []
    for message in messages:
        message_copy = message.copy()
        if message_copy["role"] == "assistant" and message_copy["content"] is not None:
            message_copy["content"] = [{"type": "text", "content": message_copy["content"]}]
        elif message_copy["role"] in ["user", "system"]:
            message_copy["content"] = [{"type": "text", "content": message_copy["content"]}]
        elif message_copy["role"] == "tool":
            message_copy["content"] = [{"type": "text", "content": message_copy["content"]}]
        converted_messages.append(message_copy)
    return converted_messages


def load_task_results(
    pipeline_name: str,
    suite_name: str,
    user_task: str,
    attack_name: str,
    injection_task: str,
    logdir: Path,
) -> TaskResults:
    path = logdir / pipeline_name / suite_name / user_task / attack_name / f"{injection_task}.json"
    with path.open() as f:
        res_dict = json.load(f)

    # Check if the result is in the old format (without content blocks)
    # Old format didn't have agentdojo_package_version field
    if "agentdojo_package_version" not in res_dict:
        # Convert messages to the new format with content blocks
        res_dict["messages"] = convert_old_messages_format(res_dict["messages"])

    return TaskResults(**res_dict)


def load_suite_results(
    suite_name: str,
    pipeline_name: str,
    attack_name: str,
    logdir=Path("../runs"),
    benchmark_version: str = "v1.2.2",
) -> tuple[dict[tuple[str, str], TaskResults], dict[tuple[str, str], TaskResults]]:
    suite = get_suite(benchmark_version, suite_name)
    results_without_injections = {}
    results_with_injections = {}

    for user_task_id in suite.user_tasks.keys():
        results_without_injections[(user_task_id, None)] = load_task_results(
            pipeline_name, suite_name, user_task_id, "none", "none", logdir
        )
        if "dos" in attack_name:
            injection_task_id = next(iter(suite.injection_tasks.keys()))
            results_with_injections[(user_task_id, injection_task_id)] = load_task_results(
                pipeline_name, suite_name, user_task_id, attack_name, injection_task_id, logdir
            )
        elif attack_name != "none":
            for injection_task_id in suite.injection_tasks.keys():
                results_with_injections[(user_task_id, injection_task_id)] = load_task_results(
                    pipeline_name, suite_name, user_task_id, attack_name, injection_task_id, logdir
                )
    return results_without_injections, results_with_injections
