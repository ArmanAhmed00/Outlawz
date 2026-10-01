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

get_article_schema = {
    "type": "function",
    "function": {
        "name": "get_article",
        "description": (
            "Return the FULL official text of one article of the GDPR or the EU AI Act, by number. "
            "Use this whenever the user names an article (e.g. 'Article 5', 'Art. 83(5)'): it is "
            "complete and exact, while search_corpus only returns fragments. Not for NIST (no articles)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "regulation": {"type": "string", "enum": ["GDPR", "EU AI Act"]},
                "article": {"type": "string", "description": "Article number only, e.g. '5' or '83'."},
            },
            "required": ["regulation", "article"],
        },
    },
}

define_term_schema = {
    "type": "function",
    "function": {
        "name": "define_term",
        "description": (
            "Return the OFFICIAL legal definition of a term from GDPR Article 4 or EU AI Act Article 3 "
            "(e.g. 'controller', 'personal data', 'deployer', 'provider', 'AI system'). Use it for "
            "'what is / what does X mean' questions; search_corpus may return passages that only "
            "USE the term."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "term": {"type": "string", "description": "The term to define, e.g. 'controller'."},
                "regulation": {"type": "string", "enum": ["GDPR", "EU AI Act", ""],
                               "description": "Optional: limit to one regulation."},
            },
            "required": ["term"],
        },
    },
}

send_message_schema = {
    "type": "function",
    "function": {
        "name": "send_message",
        "description": (
            "Propose a message to post to the team's Microsoft Teams channel. ONLY use this when "
            "the USER explicitly asks to send, share or post something. A person must approve the "
            "message before it is posted; never claim it was sent."
        ),
        "parameters": {
            "type": "object",
            "properties": {"message": {"type": "string", "description": "The exact message to post."}},
            "required": ["message"],
        },
    },
}

ALL_TOOLS = [search_corpus_schema, calculator_schema, quote_exact_schema,
             get_article_schema, define_term_schema, send_message_schema]
