import sys
sys.path.insert(0, '/home/youruser/assistant')
from components.llm import LLMClient

llm = LLMClient()
while True:
    text = input("You: ")
    response = llm.query(text)
    print("Assistant:", response)
