import asyncio
import sys
from app.llm.groq_local import ask_local

question = " ".join(sys.argv[1:]) or "What is 17 + 25?"
print(asyncio.run(ask_local(question)))
