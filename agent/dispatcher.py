import json

def build_tool_functions(index, chunks) :
    from agent.tools.calculator import calculator
    from agent.tools.corpus_tools import (make_search_corpus, make_quote_exact)
    from agent.tools.legal_tools import get_article, define_term
    from agent.tools.messaging import send_message
    
    return {
        "calculator" : calculator,
        "search_corpus" : make_search_corpus(index, chunks),
        "quote_exact" : make_quote_exact(chunks),
        "get_article" : get_article,
        "define_term" : define_term,
        "send_message" : send_message,   # only PROPOSES; a person approves in the UI
    }


def run_tool(tool_function, name, arguments_json):
    
    if name not in tool_function :
        return f"Unknown tool '{name}'."
    try:
        args = json.loads(arguments_json or "{}")
        return str(tool_function[name](**args))
    except Exception as e:
        return f"Error running {name} : {e}"
    
    