"""Async access to the local Ollama chat API; no Discord dependencies."""

import asyncio

import httpx


class OllamaError(Exception):
    """A model request failed in a way we can explain to the user."""


class OllamaClient:
    def __init__(self, base_url: str, model: str = "hermes3:8b") -> None:
        self.model = model
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), timeout=180.0, trust_env=False
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def ask(self, prompt: str) -> str:
        if not prompt.strip():
            raise ValueError("Please enter a question.")
        try:
            # Bound total time as well as HTTP inactivity time.
            async with asyncio.timeout(180):
                response = await self._http.post(
                    "/api/chat",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {"num_predict": 1024},
                    },
                )
                response.raise_for_status()
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise OllamaError("Ollama took too long. Please try again.") from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                message = f"Ollama could not find the endpoint or model. Check that {self.model} is installed."
            else:
                message = "Ollama returned an error. Check its local logs."
            raise OllamaError(message) from exc
        except httpx.RequestError as exc:
            raise OllamaError("Cannot reach Ollama. Check that it is running and OLLAMA_BASE_URL is correct.") from exc
        try:
            content = response.json()["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty model response")
            return content.strip()
        except (ValueError, KeyError, TypeError) as exc:
            raise OllamaError("Ollama returned an empty or invalid response.") from exc
