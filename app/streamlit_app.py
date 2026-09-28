"""Streamlit UI for the Outlawz RAG project.

The pipeline functions below are placeholders that return demo data so the UI
runs on its own. Replace the body of each TODO function with the real
implementation (e.g. from core.py) — the UI only depends on their signatures.
"""
import streamlit as st

TOP_K = 5
MIN_SCORE = 0.30
REFUSAL = "I don't have enough information to answer this."

DEMO_SOURCES = [
    "CELEX_02016R0679-20160504_EN_TXT.pdf",  # GDPR
    "OJ_L_202401689_EN_TXT.pdf",             # EU AI Act
    "NIST.AI.100-1.pdf",                     # NIST AI RMF
]


# ======================= Pipeline (TODO: replace) =======================
def load_index():
    """TODO: load the FAISS index and chunk list.
    Returns (index, chunks) where each chunk is {"source", "page", "text"}."""
    chunks = [
        {"source": src, "page": p, "text": f"Placeholder text for {src}, page {p}."}
        for src in DEMO_SOURCES for p in range(1, 4)
    ]
    return None, chunks


def retrieve(question, index, chunks, top_k=TOP_K):
    """TODO: embed the question and search the index.
    Returns the top_k chunks, each with an added "score" (cosine similarity)."""
    return [{**c, "score": round(0.82 - i * 0.06, 2)} for i, c in enumerate(chunks[:top_k])]


def answer_question(question, index, chunks, top_k=TOP_K, min_score=MIN_SCORE):
    """TODO: retrieve, check min_score, and call the chat model.
    Returns (answer_text, hits)."""
    hits = retrieve(question, index, chunks, top_k)
    if not hits or hits[0]["score"] < min_score:
        return REFUSAL, hits
    return (
        f"This is a placeholder answer to: *{question}*. "
        "The real answer will be generated from the retrieved passages, with citations like [1][2].",
        hits,
    )


def get_total_cost():
    """TODO: read the running API spend from the cost file."""
    return 0.0


# =============================== UI ===============================
st.set_page_config(page_title="Outlawz RAG", page_icon="⚖️", layout="wide")


@st.cache_resource(show_spinner="Loading index…")
def get_index():
    return load_index()


index, chunks = get_index()

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.header("⚙️ Settings")
    top_k = st.slider("Chunks to retrieve (top k)", 1, 15, TOP_K)
    min_score = st.slider("Min similarity to answer", 0.0, 1.0, MIN_SCORE, 0.01)

    st.divider()
    st.subheader("📚 Corpus")
    sources = sorted({c["source"] for c in chunks})
    st.caption(f"{len(chunks)} chunks from {len(sources)} documents")
    for s in sources:
        st.markdown(f"- `{s}`")

    st.divider()
    st.metric("API spend", f"${get_total_cost():.4f}", help="Budget: $5.00")

    if st.button("Rebuild index", use_container_width=True):
        get_index.clear()
        st.rerun()
    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

st.title("⚖️ Outlawz — AI Regulation Q&A")
st.caption("Ask questions about the EU AI Act, GDPR and the NIST AI RMF. Answers cite the retrieved passages.")


def render_sources(hits, min_score):
    with st.expander(f"📄 Sources ({len(hits)})"):
        for n, h in enumerate(hits, start=1):
            flag = "" if h["score"] >= min_score else " · below threshold"
            st.markdown(f"**[{n}] {h['source']}, p.{h['page']}** — similarity `{h['score']:.2f}`{flag}")
            st.caption(h["text"])


if not st.session_state.messages:
    st.info("💡 Try: *What are the principles for processing personal data under GDPR?*")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("hits"):
            render_sources(msg["hits"], msg["min_score"])

if question := st.chat_input("Ask a question…"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.spinner("Searching and answering…"):
        reply, hits = answer_question(question, index, chunks, top_k=top_k, min_score=min_score)
    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "hits": hits, "min_score": min_score}
    )
    st.rerun()
