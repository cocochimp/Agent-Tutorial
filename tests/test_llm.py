import io
import json
import unittest
from unittest.mock import patch
from estate_agent.llm import ModelClient


class ModelRequestTests(unittest.TestCase):
    def request_payload(self, base):
        # 本地HTTP替身检查请求，不发送真实网络请求、不使用真实密钥。
        response = {"choices": [{"message": {"role": "assistant", "content": None,
                     "tool_calls": []}}], "usage": {"total_tokens": 10}}
        with patch("estate_agent.llm.load_model_config", return_value={"base_url": base,
                        "model": "deepseek-flash", "api_key": "test-key"}), \
             patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(response).encode())) as send:
            client = ModelClient()
            client.decide([{"role": "user", "content": "test"}])
            request = send.call_args.args[0]
            self.assertEqual(request.full_url, base + "/chat/completions")
            self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
            return json.loads(request.data)

    def test_deepseek_disables_thinking_for_current_runtime(self):
        payload = self.request_payload("https://api.deepseek.com")
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["model"], "deepseek-flash")
        self.assertTrue(payload["tools"])

    def test_other_provider_receives_no_deepseek_option(self):
        payload = self.request_payload("http://127.0.0.1:8000/v1")
        self.assertNotIn("thinking", payload)
