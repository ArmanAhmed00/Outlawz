import json

def build_tool_functions(index, chunks) :
    from agent.tools.calculator import calculator
    from agent.tools.corpus_tools import (make_search_corpus, make_quote_exact)
    
    return {
        "calculator" : calculator,
        "search_corpus" : make_search_corpus(index, chunks),
        "quote_exact" : make_quote_exact(chunks)
    }


def run_tool(tool_function, name, arguments_json):
    
    if name not in tool_function :
        return f"Unknown tool '{name}'."
    try:
        args = json.loads(arguments_json or "{}")
        return str(tool_function[name](**args))
    except Exception as e:
        return f"Error running {name} : {e}"
    
    