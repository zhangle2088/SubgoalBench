from collections.abc import Sequence
from typing import Literal

import pytest

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
from agentdojo.agent_pipeline.pi_detector import PromptInjectionDetector
from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop
from agentdojo.benchmark import (
    _normalize_probe_template_initial_messages,
    _replace_probe_template_source_text,
)
from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime, TaskEnvironment
from agentdojo.types import ChatMessage, get_text_content_as_str, text_content_block_from_string


class NoopElement(BasePipelineElement):
    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: TaskEnvironment = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ):
        return query, runtime, env, messages, extra_args


class MockDetector(PromptInjectionDetector):
    def __init__(
        self,
        *,
        mode: Literal["message", "full_conversation"] = "message",
        should_detect=True,
    ):
        super().__init__(mode=mode)
        self.should_detect = should_detect
        self.detected_texts: list[str] = []

    def detect(self, tool_output: str) -> bool:
        self.detected_texts.append(tool_output)
        return self.should_detect


def _system(content: str) -> ChatMessage:
    return {"role": "system", "content": [text_content_block_from_string(content)]}


def _user(content: str) -> ChatMessage:
    return {"role": "user", "content": [text_content_block_from_string(content)]}


def _assistant(tool_name: str = "tool") -> ChatMessage:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [FunctionCall(function=tool_name, args={}, id=f"{tool_name}:0")],
        "reasoning_content": None,
    }


def _tool(content: str, tool_name: str = "tool") -> ChatMessage:
    tool_call = FunctionCall(function=tool_name, args={}, id=f"{tool_name}:0")
    return {
        "role": "tool",
        "content": [text_content_block_from_string(content)],
        "tool_call_id": tool_call.id,
        "tool_call": tool_call,
        "error": None,
    }


def _text(message: ChatMessage) -> str:
    content = message.get("content")
    if content is None:
        return ""
    return get_text_content_as_str(content)


def _base_messages() -> list[ChatMessage]:
    return [
        _system("template system"),
        _user("do the task"),
        _assistant(),
        _tool("clean output"),
        _assistant(),
        _tool("target injection"),
    ]


def _pipeline(system_message: str, *elements: BasePipelineElement, name: str | None = None) -> AgentPipeline:
    pipeline = AgentPipeline([SystemMessage(system_message), InitQuery(), NoopElement(), *elements])
    pipeline.name = name
    return pipeline


def test_replace_probe_template_source_text_returns_trigger_index():
    context = [
        {"role": "system", "content": "sys"},
        {"role": "tool", "content": "clean"},
        {"role": "tool", "content": "prefix attack"},
    ]

    trigger_index = _replace_probe_template_source_text(context, "prefix", "target")

    assert trigger_index == 2
    assert context[2]["content"] == "target attack"


@pytest.mark.parametrize(
    "context",
    [
        [{"role": "tool", "content": "clean"}],
        [{"role": "tool", "content": "prefix"}, {"role": "tool", "content": "prefix"}],
    ],
)
def test_replace_probe_template_source_text_rejects_missing_or_ambiguous_source(context):
    with pytest.raises(ValueError, match="expected source_prefix to occur in exactly one tool message"):
        _replace_probe_template_source_text(context, "prefix", "target")


def test_normalization_without_defense_only_replaces_system_prompt():
    messages = _base_messages()
    pipeline = _pipeline("current system")

    normalized = _normalize_probe_template_initial_messages(pipeline, messages, trigger_index=5, user_prompt="do the task")

    assert _text(normalized[0]) == "current system"
    assert [_text(message) for message in normalized[1:]] == [_text(message) for message in messages[1:]]


def test_spotlighting_normalization_replaces_system_and_delimits_tool_outputs_idempotently():
    messages = _base_messages()
    messages[3] = _tool("<<already delimited>>")
    pipeline = _pipeline(
        "current system << before them and the symbol >> after them",
        name="model-spotlighting_with_delimiting",
    )

    normalized = _normalize_probe_template_initial_messages(pipeline, messages, trigger_index=5, user_prompt="do the task")
    renormalized = _normalize_probe_template_initial_messages(
        pipeline,
        normalized,
        trigger_index=5,
        user_prompt="do the task",
    )

    assert _text(normalized[0]) == "current system << before them and the symbol >> after them"
    assert _text(normalized[3]) == "<<already delimited>>"
    assert _text(normalized[5]) == "<<target injection>>"
    assert [_text(message) for message in renormalized] == [_text(message) for message in normalized]


def test_repeat_user_prompt_normalization_inserts_after_each_tool_block_without_duplicates():
    messages = [
        _system("template system"),
        _user("do the task"),
        _assistant(),
        _tool("first tool"),
        _tool("second tool"),
        _user("do the task"),
        _assistant(),
        _tool("target injection"),
    ]
    repeat_loop = ToolsExecutionLoop([NoopElement(), InitQuery(), NoopElement()])
    pipeline = _pipeline("repeat system", repeat_loop, name="model-repeat_user_prompt")

    normalized = _normalize_probe_template_initial_messages(pipeline, messages, trigger_index=7, user_prompt="do the task")

    assert [message["role"] for message in normalized] == [
        "system",
        "user",
        "assistant",
        "tool",
        "tool",
        "user",
        "assistant",
        "tool",
        "user",
    ]
    assert _text(normalized[5]) == "do the task"
    assert _text(normalized[-1]) == "do the task"


def test_detector_normalization_checks_and_transforms_only_trigger_tool_message():
    detector = MockDetector(should_detect=True)
    pipeline = _pipeline(
        "detector system",
        ToolsExecutionLoop([NoopElement(), detector, NoopElement()]),
        name="model-transformers_pi_detector",
    )

    normalized = _normalize_probe_template_initial_messages(
        pipeline,
        _base_messages(),
        trigger_index=5,
        user_prompt="do the task",
    )

    assert detector.detected_texts == ["target injection"]
    assert _text(normalized[3]) == "clean output"
    assert _text(normalized[5]) == "<Data omitted because a prompt injection was detected>"


def test_detector_full_conversation_mode_uses_context_through_trigger_message():
    detector = MockDetector(mode="full_conversation", should_detect=False)
    pipeline = _pipeline("detector system", ToolsExecutionLoop([detector]), name="model-piguard_detector")

    normalized = _normalize_probe_template_initial_messages(
        pipeline,
        _base_messages(),
        trigger_index=5,
        user_prompt="do the task",
    )

    assert detector.detected_texts == [
        "\n".join(
            [
                "system: detector system",
                "user: do the task",
                "tool: clean output",
                "tool: target injection",
            ]
        )
    ]
    assert _text(normalized[5]) == "target injection"
