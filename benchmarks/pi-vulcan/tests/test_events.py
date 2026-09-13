from pi_vulcan.events import metrics_from_events, parse_jsonl


def test_parse_jsonl_skips_junk() -> None:
    text = "\n".join(
        [
            '{"type":"session","id":"abc"}',
            "not json",
            '{"type":"turn_start"}',
            "",
            '{"type":"tool_execution_start","toolName":"bash"}',
            '{"type":"tool_execution_end","toolName":"bash","isError":true}',
            '{"type":"message_end","message":{"usage":{"totalTokens":42}}}',
        ]
    )
    events = parse_jsonl(text)
    assert [e["type"] for e in events] == [
        "session",
        "turn_start",
        "tool_execution_start",
        "tool_execution_end",
        "message_end",
    ]
    metrics = metrics_from_events(events)
    assert metrics.turns == 1
    assert metrics.tool_calls == 1
    assert metrics.tool_errors == 1
    assert metrics.tokens == 42
    assert metrics.tool_counts == {"bash": 1}
