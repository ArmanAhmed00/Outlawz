import time
from openai import OpenAI, RateLimitError, APIError
from dotenv import load_dotenv
import os

#from agent.cost import track_cost

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def call_model(messages, tools, max_tries=3):
    for attempt in range(max_tries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                temperature=0,
            )
            #track_cost(response)
            return response
        except RateLimitError :      
            time.sleep(2 ** attempt)
        except APIError as e:
            print(f"API Error : {e}")
            time.sleep(1)
    return None
