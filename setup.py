from llama_cpp import Llama

llm = Llama(model_path="models/Llama-3.2-3B-Instruct-Q4_K_M.gguf", verbose=False)

prompt = """Parse this command into JSON format:
Command: "open firefox"

Output only JSON:
{
  "action": "launch",
  "target": "firefox"
}

Now parse: "move all PDFs to Documents"
"""

result = llm(prompt, max_tokens=100)
print(result['choices'][0]['text']) # type: ignore