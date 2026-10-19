from app.core.llm import chat, embed

vec = embed("Polyethylene film, 50 micron, food grade")
print("Embedding length:", len(vec))
print("First 3 numbers:", vec[:3])

print("Chat reply:", chat("Say hello in one short sentence."))