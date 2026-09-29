from simpleeval import simple_eval

def calculator(expression: str) -> str:
    """Evalue une expression mathématique. Renvoie le résultat ou une erreur."""
    try:
        return str(simple_eval(expression))
    except Exception as e:
        return f"Error: {e}"