import gradio as gr
 
from preparation import load_index
from answering import answer_question
 
# Load index and chunks (saved by build_index.py)
index, chunks = load_index()
 
 
def chat(message, history):
    answer, sources = answer_question(message, index, chunks)
    if sources:
        answer += "\n\n**Sources:**\n"
        seen = set()
        for s in sources:
            key = (s["source"], s["page"])
            if key not in seen:
                seen.add(key)
                answer += f"- {s['source']}, page {s['page']} (similarity {s['score']:.2f})\n"
    return answer
 
 
demo = gr.ChatInterface(fn=chat, title="📄 RAG Q&A")
demo.launch()