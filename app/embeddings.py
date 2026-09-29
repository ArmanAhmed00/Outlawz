import os
from dotenv import load_dotenv
from openai import OpenAI

from app.core import EMBED_MODEL, track_cost


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_embeddings(texts):
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    track_cost(response, is_embedding=True)
    return [item.embedding for item in response.data]



def embed_chunks(chunks, batch_size=50):
    texts = [chunk["text"] for chunk in chunks]
    embeddings = []
    for i in range(0, len(texts), batch_size):
        embeddings.extend(get_embeddings(texts[i : i+ batch_size]))
    
    return embeddings
