# Run with: streamlit run app/app.py  (from the project root)
import sys, json
from pathlib import Path

# Put the project root first so `app` resolves to the package, not this file
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from streamlit import runtime

# Launched with plain `python app/app.py`? Relaunch it through streamlit.
if not runtime.exists():
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", __file__], cwd=ROOT))

import faiss
from app.core import INDEX_FILE as _INDEX, CHUNKS_FILE as _CHUNKS
from agent.dispatcher import build_tool_functions
from agent.loop import run_agent
from agent.tools.schemas import calculator_schema, search_corpus_schema, quote_exact_schema

TOOLS = [calculator_schema, search_corpus_schema, quote_exact_schema]

INDEX_FILE = ROOT / _INDEX
CHUNKS_FILE = ROOT / _CHUNKS


@st.cache_resource
def load_index():
    index = faiss.read_index(str(INDEX_FILE))
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        chunks = json.load(f)
    return index, chunks


st.set_page_config(page_title="Outlawz", page_icon="⚖️")
st.title("⚖️ Outlawz")
st.caption("Ask a question about the documents in the corpus, or have it do the math.")

if not (INDEX_FILE.exists() and CHUNKS_FILE.exists()):
    st.error("Index not found. Run `python scripts/build_index.py` first.")
    st.stop()

index, chunks = load_index()
tool_functions = build_tool_functions(index, chunks)

if "messages" not in st.session_state:
    st.session_state.messages = []


def show_trace(trace):
    if not trace:
        return
    with st.expander(f"Agent steps ({len(trace)})"):
        for t in trace:
            st.markdown(f"**{t['tool']}** `{t['arguments']}`")
            st.text(t["result"][:500])


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        show_trace(msg.get("trace"))

if question := st.chat_input("Your question"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        trace = []
        with st.spinner("Thinking..."):
            answer = run_agent(question, TOOLS, tool_functions, verbose=False, trace=trace)
        st.markdown(answer)
        show_trace(trace)
    st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace})
