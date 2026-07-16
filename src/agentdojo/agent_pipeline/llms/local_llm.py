"""Use a locally hosted model.

Expects an OpenAI-compatible API server to be running on port 8000, e.g. launched with:

```
vllm serve /path/to/huggingface/model
```
"""

import json
import random
import re
from collections.abc import Collection, Sequence

import openai
from openai.types.chat import ChatCompletionMessageParam
from pydantic import ValidationError

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.functions_runtime import EmptyEnv, Env, Function, FunctionCall, FunctionsRuntime
from agentdojo.types import ChatAssistantMessage, ChatMessage, get_text_content_as_str, text_content_block_from_string


class InvalidModelOutputError(Exception): ...


def reformat_message(message: ChatCompletionMessageParam):
    if message["role"] == "user" or message["role"] == "assistant":
        content = ""
        if "content" in message and message["content"] is not None:
            message_content_value = message["content"]
            if isinstance(message_content_value, str):
                return message_content_value
            for message_content in message_content_value:
                if isinstance(message_content, str):
                    content += message_content
                elif "content" in message_content:
                    content += message_content["content"]
                else:
                    content += str(message_content)
                content += "\n\n"
            content = content.strip()
    else:
        content = message["content"]
    return content


def chat_completion_request(
    client: openai.OpenAI,
    model: str,
    messages: list[ChatCompletionMessageParam],
    temperature: float | None = 1.0,
    top_p: float | None = 0.9,
    max_tokens: int = 4096,
) -> str:
    try:
        reformatted_messages = []
        for message in messages:
            content = reformat_message(message)
            reformatted_messages.append({"role": message["role"], "content": content})
        response = (
            client.chat.completions.create(
                model=model,
                messages=reformatted_messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                seed=random.randint(0, 1000000),
            )
            .choices[0]
            .message.content
        )
    except Exception as e:
        print(f"[debug] error: {e}")
        response = ""
    if response is None:
        raise InvalidModelOutputError("No response from model")
    return response


_tool_calling_prompt = """# Instructions
You are a helpful assistant. You will be given a task and have access to a set of possible functions which you may call in order to generate a final answer to the question. Functions must be called one at a time, but you may continue to call additional functions if you need to before providing your final answer.

## Currently Available Functions
{functions}

## Function Calling
You may output your reasoning prior to calling a function.

If you choose to call a particular function, include the function call in the following format as part of your response:

```
<function=function_name>{{"param1": "val1", ...}}</function>
```

where the JSON inside <function=...> contains exactly the parameters for that function. Pass the arguments in correct format, i.e., strings should be enclosed in quotes, lists should be enclosed in square brackets, integers should have no quotes, etc. If there are no parameters, then you should still include an empty JSON object `{{}}` inside the <function=...> tag.

### Function Results
After calling a function, stop generating text and wait for the results of the function call in the next message. The next message will use provide the output of the function call as a JSON object. Based on the output of the function call, you may call additional functions or provide a final answer."""


def _make_system_prompt(system_message: str, tools: Collection[Function]) -> str:
    if len(tools) == 0:
        return system_message

    functions = ""
    for tool in tools:
        tool_dict = {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters.model_json_schema(),
        }
        functions += json.dumps(tool_dict, indent=2)
        functions += "\n\n"

    prompt = _tool_calling_prompt.format(functions=functions)

    if system_message:
        prompt += "\n\n" + "## Additional Instructions" + "\n\n" + system_message

    return prompt


def _parse_model_output(completion: str) -> ChatAssistantMessage:
    """Improved parsing to handle multiple function calls"""
    default_message = ChatAssistantMessage(
        role="assistant", content=[text_content_block_from_string(completion.strip())], tool_calls=[]
    )
    open_tag_pattern = re.compile(r"<function\s*=\s*([^>]+)>")
    open_match = open_tag_pattern.search(completion)
    if not open_match:
        return default_message

    # Some Llama chat templates emit a self-closing-looking opener such as
    # ``<function=get_iban/>{}`` instead of the documented
    # ``<function=get_iban>{}</function>``.
    function_name = open_match.group(1).strip().removesuffix("/").strip()

    start_idx = open_match.end()
    close_tag = "</function>"
    end_idx = completion.find(close_tag, start_idx)
    end_idx = end_idx if end_idx != -1 else len(completion)
    # Treat an empty function body, such as <function=name></function>, as {}.
    raw_json = completion[start_idx:end_idx].strip() or "{}"

    try:
        # Only consume the first JSON value. Local models occasionally emit a
        # second function call despite being instructed to call one at a time;
        # the pipeline must execute the first call and return its result before
        # considering any later call.
        params_dict, _ = json.JSONDecoder().raw_decode(raw_json)
        tool_calls = [FunctionCall(function=function_name, args=params_dict)]
    except json.JSONDecodeError:
        print(f"[debug] broken JSON: {raw_json!r}")
        return default_message
    except ValidationError:
        print(f"[debug] validation error (probably not type dict): {raw_json!r}")
        return default_message

    return ChatAssistantMessage(
        role="assistant", content=[text_content_block_from_string(completion.strip())], tool_calls=tool_calls
    )


class LocalLLM(BasePipelineElement):
    def __init__(
        self,
        client: openai.OpenAI,
        model: str,
        temperature: float | None = 0.0,
        top_p: float | None = 0.9,
        tool_delimiter: str | None = "tool",
    ) -> None:
        self.client = client
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.tool_delimiter = tool_delimiter

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env: Env = EmptyEnv(),
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, Env, Sequence[ChatMessage], dict]:
        messages_ = []
        for m in messages:
            role, content = m["role"], m["content"]
            if role == "system" and content is not None:
                content = _make_system_prompt(get_text_content_as_str(content), runtime.functions.values())
            if role == "tool":
                role = self.tool_delimiter
                if "error" in m and m["error"] is not None:
                    content = json.dumps({"error": m["error"]})
                else:
                    func_result = m["content"]
                    if func_result == "None":
                        func_result = "Success"
                    content = json.dumps({"result": func_result})
            # LocalLLM's text protocol otherwise drops structured tool calls
            # when replaying assistant messages from a probe template. Restore
            # them as <function=> text so the following tool result has a call.
            if role == "assistant" and m.get("tool_calls"):
                text = (get_text_content_as_str(content) + "\n\n") if content else ""
                for tc in m["tool_calls"]:
                    fname = tc.function if hasattr(tc, "function") else tc["function"]
                    fargs = tc.args if hasattr(tc, "args") else tc["args"]
                    text += f"<function={fname}>{json.dumps(fargs)}</function>\n\n"
                content = text.strip()
            messages_.append({"role": role, "content": content})

        completion = chat_completion_request(
            self.client,
            model=self.model,
            messages=messages_,
            temperature=self.temperature,
            top_p=self.top_p,
        )
        output = _parse_model_output(completion)
        return query, runtime, env, [*messages, output], extra_args
