import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

from src.rag_pipeline import VIRAEngine

print("Loading VIRA engine...")
engine = VIRAEngine()
print("Engine loaded! Testing...")

result = engine.chat("I have 73% attendance in one subject. What will happen?")

print("\n=== ANSWER ===")
print(result["answer"])

sources = result["sources"]
print(f"\nSources retrieved: {len(sources)}")
for i, s in enumerate(sources, 1):
    print(f"  [{i}] {s['content'][:120]}...")
