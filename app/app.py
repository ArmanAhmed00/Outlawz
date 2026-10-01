# Run with: streamlit run app/app.py  (from the project root)
import sys, json, re
from datetime import datetime
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
from app.core import USE_CLARIFY
from app.generation.clarify import check_clarity
from app.eval.injection import add_injection_chunk
from app.generation.suggest import suggest_followups
from app.export.chat_export import chat_to_pdf, chat_to_doc
from app.export.teams_export import post_chat_to_teams
from agent.tools.schemas import ALL_TOOLS
from agent.tools import messaging
from app.search.retrieval import retrieve
from app.generation.confidence import is_confident

TOOLS = ALL_TOOLS

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
    "get_article": (":material/article:", "Read the full article"),
    "define_term": (":material/menu_book:", "Looked up the official definition"),
    "send_message": (":material/send:", "Proposed a Teams message"),
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



def chat_turns(messages):
    """Pair each question with its answer and the pages it used, for the export."""
    turns = []
    for user, bot in zip(messages[::2], messages[1::2]):
        if user["role"] != "user" or bot["role"] != "assistant":
            continue
        sources = [f"{short_name(s)} p.{p}" for s, p in cited_sources(bot.get("trace", []))]
        turns.append({"question": user["content"], "answer": plain_answer(bot["content"]),
                      "sources": sources})
    return turns


@st.cache_data(show_spinner=False)
def export_pdf(turns_json):
    return chat_to_pdf(json.loads(turns_json))


@st.cache_data(show_spinner=False)
def export_doc(turns_json):
    return chat_to_doc(json.loads(turns_json))


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

# ---------------- Chats: short-term memory, kept until the page is refreshed ----------------
def new_chat():
    """Start an empty chat; drop old chats that were never used."""
    chats = st.session_state.chats
    for cid in [c for c, chat in chats.items() if not chat["messages"]]:
        del chats[cid]
    st.session_state.chat_counter += 1
    cid = st.session_state.chat_counter
    chats[cid] = {"title": "New chat", "messages": []}
    st.session_state.current_chat = cid


if "chats" not in st.session_state:
    st.session_state.chats = {}          # id -> {"title": str, "messages": [...]}
    st.session_state.chat_counter = 0
    new_chat()

current_chat = st.session_state.chats[st.session_state.current_chat]
st.session_state.messages = current_chat["messages"]  # same list: appending updates the chat

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("## ⚖️ Outlawz")
    st.caption("An AI assistant for AI & data-protection law. Every answer is grounded in the documents below and cites its pages.")

    if st.button("New chat", icon=":material/add_comment:", use_container_width=True,
                 disabled=not st.session_state.messages):
        new_chat()
        st.rerun()

    used = {cid: chat for cid, chat in st.session_state.chats.items() if chat["messages"]}
    if used:
        st.markdown("### Chats")
        st.caption("Kept until you refresh the page")
        for cid, chat in reversed(list(used.items())):   # newest first
            active = cid == st.session_state.current_chat
            if st.button(chat["title"], key=f"chat{cid}", icon=":material/chat_bubble:",
                         use_container_width=True, type="primary" if active else "secondary"):
                st.session_state.current_chat = cid
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
        ":material/calculate: Calculator  \n"
        ":material/article: Full article by number  \n"
        ":material/menu_book: Official definitions  \n"
        ":material/send: Send to Teams (needs your approval)"
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
            if msg.get("proposal"):                       # human-in-the-loop for send_message
                with st.container(border=True):
                    st.markdown(":material/send: **Message proposed for Teams**")
                    st.info(msg["proposal"])
                    status_text = msg.get("proposal_status")
                    if status_text:
                        st.caption(status_text)
                    else:
                        ok_col, no_col, _ = st.columns([1, 1, 3])
                        if ok_col.button("Approve & send", key=f"approve{id(msg)}", type="primary"):
                            ok, detail = messaging.post_to_teams(msg["proposal"])
                            msg["proposal_status"] = (f"Sent to Teams ({detail}). Check the channel to confirm it arrived."
                                                      if ok else f"Not sent: {detail}")
                            st.rerun()
                        if no_col.button("Reject", key=f"reject{id(msg)}"):
                            msg["proposal_status"] = "Rejected by you: nothing was sent."
                            st.rerun()
            if msg is st.session_state.messages[-1] and msg.get("suggestions"):
                st.caption("Follow-up questions")
                for j, sug in enumerate(msg["suggestions"]):
                    if st.button(sug, key=f"fu{len(st.session_state.messages)}_{j}",
                                 icon=":material/subdirectory_arrow_right:"):
                        clicked = sug
        else:
            st.markdown(msg["content"])

# ---------------- Download the chat (after 2+ answers) ----------------
n_answers = sum(m["role"] == "assistant" for m in st.session_state.messages)
if n_answers >= 2:
    turns_json = json.dumps(chat_turns(st.session_state.messages), ensure_ascii=False)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    with st.container(border=True):
        st.caption(f":material/download: Download or share this conversation ({n_answers} answers, with sources)")
        c1, c2, c3, _ = st.columns([1, 1, 1, 1])
        c1.download_button("PDF", data=export_pdf(turns_json), file_name=f"outlawz_chat_{stamp}.pdf",
                           mime="application/pdf", icon=":material/picture_as_pdf:",
                           use_container_width=True, on_click="ignore")
        c2.download_button("Word", data=export_doc(turns_json), file_name=f"outlawz_chat_{stamp}.doc",
                           mime="application/msword", icon=":material/description:",
                           use_container_width=True, on_click="ignore")
        with c3.popover("Teams", icon=":material/send:", use_container_width=True):
            st.markdown(f"Post this whole conversation ({n_answers} answers) to the team's Teams channel?")
            st.caption("Everyone in the channel will see it.")
            if st.button("Send to Teams", key=f"teams_send_{n_answers}", type="primary", use_container_width=True):
                ok, detail = post_chat_to_teams(json.loads(turns_json))
                if ok:
                    st.toast(f"Conversation sent to Teams ({detail}). Check the channel.", icon=":material/check_circle:")
                else:
                    st.toast(f"Not sent: {detail}", icon=":material/error:")

question = st.chat_input("Ask a legal question…") or clicked
if question:
    examples.empty()
    st.session_state.messages.append({"role": "user", "content": question})
    if current_chat["title"] == "New chat":
        current_chat["title"] = question if len(question) <= 40 else question[:37] + "..."
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
            # ask back only for vague questions that ARE on topic; off-topic ones are refused by the agent
            in_scope = USE_CLARIFY and is_confident(retrieve(question, index, chunks))
            clarification = check_clarity(question, st.session_state.messages[:-1]) if in_scope else None
            messaging.PROPOSALS.clear()
            answer = clarification or run_agent(question, TOOLS, tool_functions, verbose=False, trace=trace,
                               history=st.session_state.messages[:-1])
            trace = list(trace)
            status.update(label=f"Done · {len(trace)} step{'s' if len(trace) != 1 else ''}", expanded=False,
                          state="complete")
        st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace,
                                          "suggestions": suggest_followups(question, answer),
                                          "proposal": messaging.PROPOSALS[-1] if messaging.PROPOSALS else None})
    st.rerun()  # redraw the full history (sources, steps) and hide the examples
