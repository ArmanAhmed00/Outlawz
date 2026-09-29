def run_agent_with_trace(user_message, tools):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    trace = []   # list of (tool_name, arguments, result)

    for step in range(MAX_STEPS):
        response = call_model(messages, tools)
        if response is None:
            return {"answer": "model call failed", "trace": trace, "steps": step}

        msg = response.choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            return {"answer": msg.content, "trace": trace, "steps": step}

        for call in msg.tool_calls:
            result = run_tool(call.function.name, call.function.arguments)
            trace.append({
                "tool": call.function.name,
                "arguments": call.function.arguments,
                "result": result,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": result,
            })

    return {"answer": "reached step limit", "trace": trace, "steps": MAX_STEPS}
questions = [
    "What are the admission requirements?",         # should search once
    "What is 15% of the tuition in the guide?",     # should search then calculate
    "What documents can you search?",               # should list documents
    "What is the weather in Paris?",                # should refuse (not in corpus)
]

for q in questions:
    out = run_agent_with_trace(q, tools)
    print(f"\nQ: {q}")
    print(f"steps: {out['steps']}")
    for t in out["trace"]:
        print(f"  -> {t['tool']}({t['arguments']}) => {t['result'][:80]}")
    print(f"A: {out['answer']}")
    