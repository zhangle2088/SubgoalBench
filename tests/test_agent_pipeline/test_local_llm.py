from agentdojo.agent_pipeline.llms.local_llm import _parse_model_output, reformat_message


def test_reformat_message_preserves_string_content() -> None:
    assert reformat_message({"role": "assistant", "content": "<function=get_iban>{}</function>"}) == (
        "<function=get_iban>{}</function>"
    )


def test_parse_model_output_with_empty_arguments() -> None:
    message = _parse_model_output("<function=get_iban></function>")

    assert message["tool_calls"][0].function == "get_iban"
    assert message["tool_calls"][0].args == {}


def test_parse_model_output_with_self_closing_opener() -> None:
    message = _parse_model_output('<function=get_iban/>{}\n\n<function=send_money>{"amount": 87.5}</function>')

    assert len(message["tool_calls"]) == 1
    assert message["tool_calls"][0].function == "get_iban"
    assert message["tool_calls"][0].args == {}


def test_parse_model_output_uses_first_call_when_model_emits_multiple_calls() -> None:
    message = _parse_model_output(
        '<function=get_iban>{}</function>\n\n<function=send_money>{"amount": 87.5}</function>'
    )

    assert len(message["tool_calls"]) == 1
    assert message["tool_calls"][0].function == "get_iban"
    assert message["tool_calls"][0].args == {}
