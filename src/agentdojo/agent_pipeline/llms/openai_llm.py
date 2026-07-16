import json
import re
from collections.abc import Sequence
from types import SimpleNamespace
from typing import overload

import openai
from openai._types import NOT_GIVEN
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionDeveloperMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionMessageToolCallParam,
    ChatCompletionReasoningEffort,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params import FunctionDefinition
from tenacity import retry, retry_if_not_exception_type, stop_after_attempt, wait_random_exponential

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, Function, FunctionCall, FunctionsRuntime
from agentdojo.types import (
    ChatAssistantMessage,
    ChatMessage,
    ChatSystemMessage,
    ChatToolResultMessage,
    ChatUserMessage,
    MessageContentBlock,
    get_text_content_as_str,
    text_content_block_from_string,
)


def _sanitize_openai_tool_call_id(tool_call_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", tool_call_id)


def _tool_call_to_openai(tool_call: FunctionCall, sanitize_id: bool = False) -> ChatCompletionMessageToolCallParam:
    if tool_call.id is None:
        raise ValueError("`tool_call.id` is required for OpenAI")
    tool_call_id = _sanitize_openai_tool_call_id(tool_call.id) if sanitize_id else tool_call.id
    return ChatCompletionMessageToolCallParam(
        id=tool_call_id,
        type="function",
        function={
            "name": tool_call.function,
            "arguments": json.dumps(tool_call.args),
        },
    )


_REASONING_MODELS = {"o1", "o3"}


def _is_reasoning_model(model_name: str) -> bool:
    return any(model in model_name for model in _REASONING_MODELS)


def _is_kimi_model(model_name: str) -> bool:
    model_name = model_name.lower()
    return "kimi" in model_name or "mimo" in model_name or "xiaomi" in model_name


def _is_claude_model(model_name: str) -> bool:
    return "claude" in model_name.lower()


def _is_minimax_model(model_name: str) -> bool:
    return "minimax" in model_name.lower()


def _is_qwen_model(model_name: str) -> bool:
    return "qwen" in model_name.lower()


def _is_gpt_oss_model(model_name: str) -> bool:
    return "gpt-oss" in model_name.lower()


def _is_llama4_model(model_name: str) -> bool:
    return "llama-4" in model_name.lower() or "llama_4" in model_name.lower()


@overload
def _content_blocks_to_openai_content_blocks(
    message: ChatUserMessage | ChatSystemMessage,
) -> list[ChatCompletionContentPartTextParam]: ...


@overload
def _content_blocks_to_openai_content_blocks(
    message: ChatAssistantMessage | ChatToolResultMessage,
) -> list[ChatCompletionContentPartTextParam] | None: ...


def _content_blocks_to_openai_content_blocks(
    message: ChatUserMessage | ChatAssistantMessage | ChatSystemMessage | ChatToolResultMessage,
) -> list[ChatCompletionContentPartTextParam] | None:
    if message["content"] is None:
        return None
    return [ChatCompletionContentPartTextParam(type="text", text=el["content"] or "") for el in message["content"]]


def _message_to_openai(message: ChatMessage, model_name: str) -> ChatCompletionMessageParam:
    is_deepseek = "deepseek" in model_name.lower()
    is_kimi = _is_kimi_model(model_name)
    is_claude = _is_claude_model(model_name)
    is_minimax = _is_minimax_model(model_name)
    is_qwen = _is_qwen_model(model_name)
    # DeepSeek V4 Flash without thinking mode may return reasoning_content
    is_deepseek_v4_flash = "deepseek-v4" in model_name.lower()
    match message["role"]:
        case "system":
            # Some OpenAI-compatible providers do not support 'developer' role.
            if is_deepseek or is_kimi or is_claude or is_minimax or is_qwen:
                return ChatCompletionSystemMessageParam(
                    role="system", content=_content_blocks_to_openai_content_blocks(message)
                )
            return ChatCompletionDeveloperMessageParam(
                role="developer", content=_content_blocks_to_openai_content_blocks(message)
            )
        case "user":
            return ChatCompletionUserMessageParam(
                role="user", content=_content_blocks_to_openai_content_blocks(message)
            )
        case "assistant":
            if message["tool_calls"] is not None and len(message["tool_calls"]) > 0:
                tool_calls = [_tool_call_to_openai(tool_call, sanitize_id=is_claude) for tool_call in message["tool_calls"]]
                content = _content_blocks_to_openai_content_blocks(message)
                # For Kimi, ensure content is None if empty (not an empty list)
                if is_kimi and content is not None and len(content) == 0:
                    content = None
                # For Kimi with reasoning_content, use dict format to include extra fields
                if is_kimi and message.get("reasoning_content"):
                    return {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls,
                        "reasoning_content": message.get("reasoning_content"),
                    }
                return ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=content,
                    tool_calls=tool_calls,
                )
            content = _content_blocks_to_openai_content_blocks(message)
            if is_kimi and content is not None and len(content) == 0:
                content = None
            if is_kimi and message.get("reasoning_content"):
                return {
                    "role": "assistant",
                    "content": content,
                    "reasoning_content": message.get("reasoning_content"),
                }
            return ChatCompletionAssistantMessageParam(
                role="assistant",
                content=content,
            )
        case "tool":
            if message["tool_call_id"] is None:
                raise ValueError("`tool_call_id` should be specified for OpenAI.")
            # DeepSeek, Kimi, MiniMax, and Qwen expect string content for tool messages, not array
            if is_deepseek or is_kimi or is_minimax or is_qwen:
                content = message["error"] or get_text_content_as_str(message["content"])
            else:
                content = message["error"] or _content_blocks_to_openai_content_blocks(message)
            return ChatCompletionToolMessageParam(
                content=content,
                tool_call_id=_sanitize_openai_tool_call_id(message["tool_call_id"]) if is_claude else message["tool_call_id"],
                role="tool",
                name=message["tool_call"].function,  # type: ignore -- this is actually used, and is important!
            )
        case _:
            raise ValueError(f"Invalid message type: {message}")


def _openai_to_tool_call(tool_call: ChatCompletionMessageToolCall) -> FunctionCall:
    return FunctionCall(
        function=tool_call.function.name,
        args=json.loads(tool_call.function.arguments),
        id=tool_call.id,
    )


def _assistant_message_to_content(message: ChatCompletionMessage) -> list[MessageContentBlock] | None:
    if message.content is None:
        return None
    # If content is empty string, return None instead of empty block
    if message.content == "":
        return None
    return [text_content_block_from_string(message.content)]


def _openai_to_assistant_message(message: ChatCompletionMessage) -> ChatAssistantMessage:
    if message.tool_calls is not None:
        # Add tolerance for malformed tool calls from API responses
        tool_calls = []
        for tool_call in message.tool_calls:
            try:
                temp = _openai_to_tool_call(tool_call)
                tool_calls.append(temp)
            except Exception:
                continue
    else:
        tool_calls = None
    # Extract reasoning_content for thinking models like Kimi k2.5
    # Note: Gemini's reasoning_details are encrypted and not human-readable, so we skip them
    reasoning_content = getattr(message, "reasoning_content", None) or None
    return ChatAssistantMessage(
        role="assistant",
        content=_assistant_message_to_content(message),
        tool_calls=tool_calls,
        reasoning_content=reasoning_content,
    )


def _aggregate_chat_stream(stream) -> SimpleNamespace:
    """Aggregate a streaming chat completion into a message-shaped object.

    Workaround for gpt-oss under vLLM: non-streaming responses drop the
    commentary-channel tool calls (finish_reason=stop, content=None,
    tool_calls=[]), while streaming correctly emits them. This rebuilds a
    ``ChatCompletionMessage``-compatible object from the streamed deltas so
    ``_openai_to_assistant_message`` works unchanged.
    """
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_calls: dict[int, dict] = {}
    order: list[int] = []
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None):
            content_parts.append(delta.content)
        rc = getattr(delta, "reasoning", None) or getattr(delta, "reasoning_content", None)
        if rc:
            reasoning_parts.append(rc)
        for tc in getattr(delta, "tool_calls", None) or []:
            idx = tc.index if tc.index is not None else 0
            if idx not in tool_calls:
                tool_calls[idx] = {"id": None, "function": {"name": "", "arguments": ""}}
                order.append(idx)
            slot = tool_calls[idx]
            if tc.id:
                slot["id"] = tc.id
            if tc.function:
                if tc.function.name:
                    slot["function"]["name"] += tc.function.name
                if tc.function.arguments:
                    slot["function"]["arguments"] += tc.function.arguments
    content = "".join(content_parts) or None
    reasoning_content = "".join(reasoning_parts) or None
    tc_list = None
    if tool_calls:
        tc_list = [
            ChatCompletionMessageToolCall(
                id=tool_calls[idx]["id"] or f"call_{idx}",
                type="function",
                function={
                    "name": tool_calls[idx]["function"]["name"],
                    "arguments": tool_calls[idx]["function"]["arguments"],
                },
            )
            for idx in order
        ]
    return SimpleNamespace(
        content=content,
        tool_calls=tc_list,
        reasoning_content=reasoning_content,
    )


def _function_to_openai(f: Function) -> ChatCompletionToolParam:
    function_definition = FunctionDefinition(
        name=f.name,
        description=f.description,
        parameters=f.parameters.model_json_schema(),
    )
    return ChatCompletionToolParam(type="function", function=function_definition)


@retry(
    wait=wait_random_exponential(multiplier=1, max=40),
    stop=stop_after_attempt(3),
    reraise=True,
    retry=retry_if_not_exception_type((openai.BadRequestError, openai.UnprocessableEntityError)),
)
def chat_completion_request(
    client: openai.OpenAI,
    model: str,
    messages: Sequence[ChatCompletionMessageParam],
    tools: Sequence[ChatCompletionToolParam],
    reasoning_effort: ChatCompletionReasoningEffort | None,
    temperature: float | None = 0.0,
    seed: int | None = 42,
    logprobs: bool = False,
    top_logprobs: int | None = None,
    max_tokens: int | None = None,
    deterministic: bool = False,
):
    extra_body = None
    if _is_kimi_model(model):
        # Kimi doesn't support reasoning_effort
        reasoning_effort = None
        # Disable thinking mode for kimi-k2.5/k2.6
        extra_body = {"thinking": {"type": "disabled"}}
        # kimi API only accepts temperature=0.6, deterministic mode unavailable
        temperature = 0.6
    elif "gpt-5.5" in model.lower():
        # GPT-5.5 only supports temperature=1
        temperature = 1.0
    elif "deepseek-v4" in model.lower():
        # Disable thinking mode for DeepSeek V4 Flash
        extra_body = {"thinking": {"type": "disabled"}}

    # OpenRouter provider routing：消除各模型默认路由 provider 的 tool-call 问题。
    if "openrouter" in str(client.base_url).lower():
        if _is_llama4_model(model) and "scout" not in model.lower():
            # Llama 4 Maverick: DigitalOcean/Parasail 长上下文后退化成文本伪调用 [func(...)]，强制 Google。
            # Scout 例外：17B 在 Google 路由下返回空响应，走默认路由更稳。
            extra_body = {**(extra_body or {}), "provider": {"only": ["Google"]}}
        elif _is_gpt_oss_model(model):
            # gpt-oss-120b: SambaNova 偶发上游 undefined 错误（streaming 中断），排除。
            extra_body = {**(extra_body or {}), "provider": {"ignore": ["SambaNova"]}}

    # gpt-oss under vLLM drops tool_calls in non-streaming responses; stream
    # and aggregate instead. Skip when logprobs are requested (probe path,
    # which does not rely on tool calls).
    if _is_gpt_oss_model(model) and not logprobs:
        # gpt-oss occasionally emits malformed harmony tokens (<|constrain|>,
        # reasoning leaking into the commentary header) on complex multi-tool
        # turns; vLLM's streaming parser then fails with APIError
        # "unexpected tokens remaining in message header". On that specific
        # error, raise temperature and retry so the model regenerates a clean
        # sequence. Other errors propagate immediately.
        base_temp = temperature if temperature is not None else 0.0
        last_exc: Exception | None = None
        temps = [base_temp, 0.3, 0.6, 1.0]
        for idx, retry_temp in enumerate(temps):
            try:
                # 升温重试(idx>0)时去掉 seed，让采样真正随机以避开错误格式
                use_seed = seed if idx == 0 else None
                stream = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools or NOT_GIVEN,
                    tool_choice="auto" if tools else NOT_GIVEN,
                    temperature=retry_temp if retry_temp is not None else NOT_GIVEN,
                    reasoning_effort=reasoning_effort or NOT_GIVEN,
                    seed=use_seed if use_seed is not None else NOT_GIVEN,
                    max_tokens=max_tokens or NOT_GIVEN,
                    extra_body=extra_body,
                    stream=True,
                )
                message = _aggregate_chat_stream(stream)
                return SimpleNamespace(
                    choices=[SimpleNamespace(index=0, message=message, finish_reason="stop")]
                )
            except openai.APIError as e:
                emsg = str(e)
                last_exc = e
                if "unexpected tokens" not in emsg and "message header" not in emsg:
                    raise
                continue
        assert last_exc is not None
        raise last_exc
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools or NOT_GIVEN,
        tool_choice="auto" if tools else NOT_GIVEN,
        temperature=temperature if temperature is not None else NOT_GIVEN,
        reasoning_effort=reasoning_effort or NOT_GIVEN,
        seed=seed or NOT_GIVEN,
        logprobs=logprobs if logprobs else NOT_GIVEN,
        top_logprobs=top_logprobs if logprobs else NOT_GIVEN,
        max_tokens=max_tokens or NOT_GIVEN,
        extra_body=extra_body,
        stream=False,
    )
    # Validate response has choices
    if not response.choices or len(response.choices) == 0:
        raise ValueError(f"API returned empty choices for model {model}")
    return response


def extract_token_logprob(choice, target_tokens: set[str]) -> dict[str, float]:
    """从 response choice 的 top_logprobs 中提取目标 token 的概率。

    Args:
        choice: OpenAI API response 的一个 choice 对象。
        target_tokens: 需要提取的目标 token 集合（如 {"YES", "Yes", "yes"}）。

    Returns:
        字典，键为匹配到的 token 文本，值为概率（0-1）。
    """
    result = {}
    if not hasattr(choice, "logprobs") or choice.logprobs is None:
        return result
    content = choice.logprobs.content
    if not content or len(content) == 0:
        return result
    token_candidates = [content[0], *reversed(content[1:])]
    for token in token_candidates:
        if token.token not in target_tokens:
            continue
        if not hasattr(token, "top_logprobs") or token.top_logprobs is None:
            continue
        for token_logprob in token.top_logprobs:
            if token_logprob.token in target_tokens:
                import math

                result[token_logprob.token] = math.exp(token_logprob.logprob)
        return result
    first_token = content[0]
    if not hasattr(first_token, "top_logprobs") or first_token.top_logprobs is None:
        return result
    for token_logprob in first_token.top_logprobs:
        if token_logprob.token in target_tokens:
            import math

            result[token_logprob.token] = math.exp(token_logprob.logprob)
    return result


class OpenAILLM(BasePipelineElement):
    """LLM pipeline element that uses OpenAI's API.

    Args:
        client: The OpenAI client.
        model: The model name.
        temperature: The temperature to use for generation.
    """

    def __init__(
        self,
        client: openai.OpenAI,
        model: str,
        reasoning_effort: ChatCompletionReasoningEffort | None = None,
        temperature: float | None = 0.0,
        seed: int | None = 42,
        deterministic: bool = False,
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.reasoning_effort: ChatCompletionReasoningEffort | None = reasoning_effort
        self.deterministic = deterministic

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        openai_messages = [_message_to_openai(message, self.model) for message in messages]
        openai_tools = [_function_to_openai(tool) for tool in runtime.functions.values()]
        completion = chat_completion_request(
            self.client, self.model, openai_messages, openai_tools, self.reasoning_effort, self.temperature, self.seed,
            deterministic=self.deterministic,
        )
        output = _openai_to_assistant_message(completion.choices[0].message)
        messages = [*messages, output]
        return query, runtime, env, messages, extra_args


class OpenAILLMToolFilter(BasePipelineElement):
    def __init__(self, prompt: str, client: openai.OpenAI, model: str, reasoning_effort: ChatCompletionReasoningEffort | None = None, temperature: float | None = 0.0, seed: int | None = 42) -> None:
        self.prompt = prompt
        self.client = client
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.reasoning_effort: ChatCompletionReasoningEffort | None = reasoning_effort

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        messages = [*messages, ChatUserMessage(role="user", content=[text_content_block_from_string(self.prompt)])]
        openai_messages = [_message_to_openai(message, self.model) for message in messages]
        openai_tools = [_function_to_openai(tool) for tool in runtime.functions.values()]
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            tools=openai_tools or NOT_GIVEN,
            tool_choice="none",
            temperature=self.temperature if self.temperature is not None else NOT_GIVEN,
            reasoning_effort=self.reasoning_effort or NOT_GIVEN,
            seed=self.seed or NOT_GIVEN,
            stream=False,
        )
        output = _openai_to_assistant_message(completion.choices[0].message)

        new_tools = {}
        for tool_name, tool in runtime.functions.items():
            if output["content"] is not None and tool_name in get_text_content_as_str(output["content"]):
                new_tools[tool_name] = tool

        runtime.update_functions(new_tools)

        messages = [*messages, output]
        return query, runtime, env, messages, extra_args
