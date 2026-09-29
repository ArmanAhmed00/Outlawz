calculator_schema = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": (
            "Evaluate a math expression and return the result. "
            "Use this for any arithmetic instead of computing in your head."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A math expression, e.g. '10000 * 0.15'",
                }
            },
            "required": ["expression"],
        },
    },
}

search_corpus_schema = {
    "type": "function",
    "function": {
        "name": "search_corpus",
        "description": (
            "Search the document corpus (GDPR, AI Act, etc.) for passages relevant "
            "to a query. Use this whenever you need information from the documents. "
            "Returns the top matching passages with their source and page."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for, in natural language.",
                },
                "k": {
                    "type": "integer",
                    "description": "Number of passages to retrieve (default 5).",
                },
            },
            "required": ["query"],
        },
    },
}

quote_exact_schema = {
    "type": "function",
    "function": {
        "name": "quote_exact",
        "description": (
            "Retrieve the exact text of a chunk given its source file and page number. "
            "Use this to verify a quote before citing it precisely."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Exact source filename."},
                "page": {"type": "integer", "description": "Page number."},
            },
            "required": ["source", "page"],
        },
    },
}