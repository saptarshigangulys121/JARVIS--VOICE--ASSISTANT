import json
import urllib.error
import urllib.request


OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"


def ask_ollama(prompt):
    request_data = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are Jarvis, a helpful voice assistant. Keep answers concise and easy to speak aloud.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(request_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
    except urllib.error.URLError as error:
        raise RuntimeError(
            "Ollama is not running. Start Ollama and try again."
        ) from error
    except (TimeoutError, json.JSONDecodeError) as error:
        raise RuntimeError("Ollama did not return a valid response.") from error

    answer = result.get("message", {}).get("content", "").strip()
    if not answer:
        raise RuntimeError("Ollama returned an empty response.")
    return answer
