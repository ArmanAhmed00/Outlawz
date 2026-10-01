# Run with: streamlit run app/app.py  (from the project root)
import sys, json, re
from collections import Counter
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
from app.core import INDEX_FILE as _INDEX, CHUNKS_FILE as _CHUNKS, get_total_cost
from agent.dispatcher import build_tool_functions
from agent.loop import run_agent
from app.eval.injection import add_injection_chunk
from app.generation.suggest import suggest_followups
from agent.tools.schemas import calculator_schema, search_corpus_schema, quote_exact_schema

TOOLS = [calculator_schema, search_corpus_schema, quote_exact_schema]

INDEX_FILE = ROOT / _INDEX
CHUNKS_FILE = ROOT / _CHUNKS
BUDGET = 5.00  # team budget in $, same as the cost tracker

# Friendly names for the corpus files
DOCUMENT_TITLES = {
    "CELEX_02016R0679-20160504_EN_TXT.pdf": ("GDPR", "Regulation (EU) 2016/679"),
    "OJ_L_202401689_EN_TXT.pdf": ("EU AI Act", "Regulation (EU) 2024/1689"),
    "NIST.AI.100-1.pdf": ("NIST AI RMF", "AI Risk Management Framework 1.0"),
}

TOOL_LABELS = {
    "search_corpus": (":material/search:", "Searched the documents"),
    "quote_exact": (":material/format_quote:", "Checked the exact text"),
    "calculator": (":material/calculate:", "Calculated"),
}

EXAMPLES = [
    "What is the definition of personal data under the GDPR?",
    "What are the obligations for providers of high-risk AI systems?",
    "What is 4% of a €250M annual turnover?",
    "What are the four functions of the NIST AI RMF?",
]


@st.cache_resource
def load_index():
    index = faiss.read_index(str(INDEX_FILE))
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        chunks = json.load(f)
    return add_injection_chunk(index, chunks)  # no-op unless INJECTION_TEST


def short_name(source):
    return DOCUMENT_TITLES.get(source, (source, ""))[0]


def clean_answer(text):
    """Drop the model's 【3†source】 tags; the model writes \\( ... \\) but Streamlit wants $ ... $."""
    text = re.sub(r"\s*【[^】]*】", "", text)
    text = re.sub(r"\\\((.+?)\\\)", r"$\1$", text)
    return re.sub(r"\\\[(.+?)\\\]", r"$$\1$$", text, flags=re.S)


def plain_answer(text):
    """Answer text for the clipboard: no 【3†source】 tags and no math markers."""
    text = re.sub(r"\s*【[^】]*】", "", text)
    return re.sub(r"\\[()\[\]]\s?|\s?\\[)\]]", "", text).strip()


def cited_sources(trace):
    """(source, page) pairs the agent looked at, in order, without duplicates."""
    found = []
    for t in trace:
        if t["tool"] == "quote_exact":
            try:
                args = json.loads(t["arguments"])
                found.append((args["source"], int(args["page"])))
            except (ValueError, KeyError, TypeError):
                pass
        elif t["tool"] == "search_corpus":
            found += [(s, int(p)) for s, p in re.findall(r"^\[(\S+) p\.(\d+)", t["result"], re.M)]
    return list(dict.fromkeys(found))


def show_steps(trace):
    for t in trace:
        icon, label = TOOL_LABELS.get(t["tool"], (":material/build:", t["tool"]))
        try:
            args = json.loads(t["arguments"])
            detail = args.get("query") or args.get("expression") or \
                f"{short_name(args.get('source', ''))} p.{args.get('page', '?')}"
        except (ValueError, AttributeError):
            detail = t["arguments"]
        st.markdown(f"{icon} **{label}** · `{detail}`")
        with st.expander("Result", expanded=False):
            st.text(t["result"][:1500])


def copy_button(text):
    """A small button that copies text to the clipboard (Streamlit has no built-in one)."""
    # Escape < > & so model output can never close the <script> tag
    payload = json.dumps(text).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    st.iframe(f"""
    <button id="copy">&#x2398;&nbsp; Copy</button>
    <style>
      body {{ margin: 0; }}
      #copy {{ font: 14px "Source Sans Pro", sans-serif; color: #1C1C1C; background: #FAF8F4;
               border: 1px solid rgba(49, 51, 63, 0.2); border-radius: 8px; padding: 6px 12px;
               cursor: pointer; height: 38px; }}
      #copy:hover {{ border-color: #1F3A5F; color: #1F3A5F; }}
    </style>
    <script>
      const text = {payload};
      const btn = document.getElementById("copy");
      btn.onclick = async () => {{
        try {{ await navigator.clipboard.writeText(text); }}
        catch (e) {{  // older browsers / blocked clipboard API
          const ta = document.createElement("textarea");
          ta.value = text; document.body.appendChild(ta); ta.select();
          document.execCommand("copy"); ta.remove();
        }}
        btn.innerHTML = "&#x2713;&nbsp; Copied";
        setTimeout(() => btn.innerHTML = "&#x2398;&nbsp; Copy", 1500);
      }};
    </script>
    """, height=40)


def show_answer(content, trace):
    answer = clean_answer(content)
    st.markdown(answer)
    sources = cited_sources(trace)
    copy_col, sources_col = st.columns([1, 5], vertical_alignment="center")
    with copy_col:
        copy_button(plain_answer(content))
    if sources:
        with sources_col.popover(f":material/menu_book: Pages consulted ({len(sources)})"):
            for source, page in sources:
                name, full = DOCUMENT_TITLES.get(source, (source, ""))
                st.markdown(f"**{name}**, page {page}  \n:gray[{full}]")
    if trace:
        with st.expander(f":material/account_tree: How I got this ({len(trace)} step{'s' if len(trace) != 1 else ''})"):
            show_steps(trace)


# ---------------- Page ----------------
st.set_page_config(page_title="Outlawz", page_icon="⚖️", layout="centered")
st.markdown("""
<style>
  .block-container { padding-top: 2.5rem; max-width: 820px; }
  h1, h1 span { font-family: Georgia, 'Times New Roman', serif !important; letter-spacing: -0.5px; }
  [data-testid="stSidebar"] h3 { font-size: 0.95rem; margin-bottom: 0.25rem; }
  .stButton > button { text-align: left; justify-content: flex-start; }
</style>
""", unsafe_allow_html=True)

if not (INDEX_FILE.exists() and CHUNKS_FILE.exists()):
    st.error("Index not found. Run `python scripts/ingest/build_index.py` first.", icon=":material/error:")
    st.stop()

index, chunks = load_index()
tool_functions = build_tool_functions(index, chunks)

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("## ⚖️ Outlawz")
    st.caption("An AI assistant for AI & data-protection law. Every answer is grounded in the documents below and cites its pages.")

    if st.button("New chat", icon=":material/add_comment:", use_container_width=True,
                 disabled=not st.session_state.messages):
        st.session_state.messages = []
        st.rerun()

    st.markdown("### Documents")
    counts = Counter(c["source"] for c in chunks)
    for source, n in counts.most_common():
        name, full = DOCUMENT_TITLES.get(source, (source, ""))
        st.markdown(f":material/description: **{name}**  \n:gray[{full} · {n} passages]")

    st.markdown("### Tools")
    st.markdown(
        ":material/search: Search the documents  \n"
        ":material/format_quote: Quote a page exactly  \n"
        ":material/calculate: Calculator"
    )

    st.markdown("### Team spend")
    spent = get_total_cost()
    st.progress(min(spent / BUDGET, 1.0), text=f"\\${spent:.4f} of \\${BUDGET:.2f}")  # escaped $ so it is not read as math

# ---------------- Chat ----------------
st.title("Outlawz")
st.caption("Ask about the GDPR, the EU AI Act or the NIST AI RMF, or have it do the math.")

clicked = None
examples = st.empty()  # cleared as soon as a question is asked
if not st.session_state.messages:
    with examples.container(border=True):
        st.markdown("**Try one of these**")
        cols = st.columns(2)
        for i, example in enumerate(EXAMPLES):
            if cols[i % 2].button(example, key=f"ex{i}", use_container_width=True):
                clicked = example

AVATARS = {"user": ":material/person:", "assistant": ":material/gavel:"}

for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar=AVATARS[msg["role"]]):
        if msg["role"] == "assistant":
            show_answer(msg["content"], msg.get("trace", []))
            if msg is st.session_state.messages[-1] and msg.get("suggestions"):
                st.caption("Follow-up questions")
                for j, sug in enumerate(msg["suggestions"]):
                    if st.button(sug, key=f"fu{len(st.session_state.messages)}_{j}",
                                 icon=":material/subdirectory_arrow_right:"):
                        clicked = sug
        else:
            st.markdown(msg["content"])

question = st.chat_input("Ask a legal question…") or clicked
if question:
    examples.empty()
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar=AVATARS["user"]):
        st.markdown(question)

    with st.chat_message("assistant", avatar=AVATARS["assistant"]):
        with st.status("Researching…", expanded=True) as status:
            class LiveTrace(list):
                """Shows each tool call in the status box as soon as the agent makes it."""
                def append(self, step):
                    super().append(step)
                    icon, label = TOOL_LABELS.get(step["tool"], (":material/build:", step["tool"]))
                    status.update(label=f"{label}…")
                    status.markdown(f"{icon} {label} · `{step['arguments']}`")

            trace = LiveTrace()
            answer = run_agent(question, TOOLS, tool_functions, verbose=False, trace=trace,
                               history=st.session_state.messages[:-1])
            trace = list(trace)
            status.update(label=f"Done · {len(trace)} step{'s' if len(trace) != 1 else ''}", expanded=False,
                          state="complete")
        st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace,
                                          "suggestions": suggest_followups(question, answer)})
    st.rerun()  # redraw the full history (sources, steps) and hide the examples
