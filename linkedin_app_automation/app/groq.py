from groq import Groq
import json
from dotenv import load_dotenv
import os

with open("app/config.json") as f:
    config = json.load(f)
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def enhance_content(text: str) -> str:
    prompt = f"Paraphrase this for LinkedIn (under 100 words):\n{text}"
    res = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        max_tokens=150,
        temperature=0.7
    )
    return res.choices[0].message.content.strip()

def generate_content(prompt: str, n: int = 3) -> list[tuple[str, int]]:
    variations = []
    for i in range(n):
        full_prompt = f"Generate a 100-word LinkedIn post for this prompt (variation {i+1}): {prompt}"
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": full_prompt}],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=150,
            temperature=0.8
        )
        variations.append((res.choices[0].message.content.strip(), i + 1))
    return variations
