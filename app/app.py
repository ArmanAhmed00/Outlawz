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
from app.core import TOP_K, INDEX_FILE as _INDEX, CHUNKS_FILE as _CHUNKS
from app.generate_answer import answer_question

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
st.caption("Ask a question about the documents in the corpus.")

if not (INDEX_FILE.exists() and CHUNKS_FILE.exists()):
    st.error("Index not found. Run `python scripts/build_index.py` first.")
    st.stop()

index, chunks = load_index()

if "messages" not in st.session_state:
    st.session_state.messages = []


def show_sources(sources):
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})"):
        for s in sources:
            st.markdown(f"**{s['source']}**, p.{s['page']} — score {s['score']:.3f}")
            st.text(s["text"][:500])


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        show_sources(msg.get("sources"))

if question := st.chat_input("Your question"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            answer, sources = answer_question(question, index, chunks, k=TOP_K)
        st.markdown(answer)
        show_sources(sources)
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
