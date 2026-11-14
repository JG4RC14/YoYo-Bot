import unittest
from unittest.mock import AsyncMock

import httpx

from src.bot import YoYoBot
from src.llm.ollama_client import OllamaClient, OllamaError


class OllamaTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, handler):
        client = OllamaClient("http://localhost:11434")
        await client.close()
        client._http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://localhost:11434"
        )
        self.addAsyncCleanup(client.close)
        return client

    async def test_request_and_answer(self):
        import json

        def handler(request):
            self.assertEqual(request.url.path, "/api/chat")
            self.assertEqual(json.loads(request.content), {
                "model": "hermes3:8b",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": False,
                "options": {"num_predict": 1024},
            })
            return httpx.Response(200, json={"message": {"content": " Hi! "}})

        client = await self.request(handler)
        self.assertEqual(await client.ask("Hello"), "Hi!")

    async def test_invalid_and_error_responses(self):
        for status, body in [(200, {}), (200, {"message": {"content": ""}}), (404, {}), (500, {})]:
            with self.subTest(status=status, body=body):
                client = await self.request(lambda request: httpx.Response(status, json=body))
                with self.assertRaises(OllamaError):
                    await client.ask("Hello")

    async def test_connection_and_timeout(self):
        for error in [httpx.ConnectError, httpx.ReadTimeout]:
            def handler(request):
                raise error("unavailable", request=request)

            client = await self.request(handler)
            with self.assertRaises(OllamaError):
                await client.ask("Hello")


class DiscordTests(unittest.IsolatedAsyncioTestCase):
    async def test_defer_before_generation_and_long_reply(self):
        from types import SimpleNamespace

        interaction = SimpleNamespace(response=AsyncMock(), followup=AsyncMock())

        async def generate(prompt):
            interaction.response.defer.assert_awaited_once_with(thinking=True)
            return "x" * 2001

        bot = SimpleNamespace(ollama=SimpleNamespace(ask=AsyncMock(side_effect=generate)))
        await YoYoBot.ask(bot, interaction, "Hello")
        kwargs = interaction.followup.send.call_args.kwargs
        self.assertEqual(kwargs["file"].fp.read(), b"x" * 2001)
        kwargs["file"].close()

    async def test_blank_prompt_never_calls_model(self):
        from types import SimpleNamespace

        interaction = SimpleNamespace(response=AsyncMock(), followup=AsyncMock())
        bot = SimpleNamespace(ollama=SimpleNamespace(ask=AsyncMock()))
        await YoYoBot.ask(bot, interaction, "  ")
        bot.ollama.ask.assert_not_awaited()
        self.assertTrue(interaction.response.send_message.call_args.kwargs["ephemeral"])
