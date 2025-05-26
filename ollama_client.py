import requests

class OllamaLLM:
    def __init__(self, model="gemma:4b", host="http://localhost:11434"):
        self.model = model
        self.url = f"{host}/api/generate"

    def __call__(self, prompt, max_length=200, do_sample=False):
        response = requests.post(self.url, json={
            "model": self.model,
            "prompt": prompt,
            "stream": False
        })
        response.raise_for_status()
        return [{"generated_text": response.json()["response"]}]
