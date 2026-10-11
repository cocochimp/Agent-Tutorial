import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from estate_agent.business import DemoError
from estate_agent.config import load_model_config
from estate_agent.llm import ModelClient


class ModelConfigTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "deepseek_config.json"
        config_patch = patch("estate_agent.config.CONFIG_PATH", self.path)
        config_patch.start()
        self.addCleanup(config_patch.stop)
        env_patch = patch.dict("os.environ", {}, clear=True)
        env_patch.start()
        self.addCleanup(env_patch.stop)

    def write(self, key, encoding="utf-8"):
        self.path.write_text(json.dumps({"api_key": key}), encoding=encoding)

    def test_file_key_loads_with_defaults(self):
        self.write(" test-secret ", encoding="utf-8-sig")
        client = ModelClient()
        self.assertEqual(client.base, "https://api.deepseek.com")
        self.assertEqual(client.model, "deepseek-flash")
        self.assertEqual(client.key, "test-secret")

    def test_file_is_reloaded_for_next_request(self):
        self.write("first-test-secret")
        self.assertEqual(ModelClient().key, "first-test-secret")
        self.write("second-test-secret")
        self.assertEqual(ModelClient().key, "second-test-secret")

    def test_filled_file_overrides_environment_without_mixing(self):
        self.write("file-secret")
        with patch.dict("os.environ", {"AGENT_BASE_URL": "http://localhost:8000/v1", "AGENT_API_KEY": "env-secret"}):
            config = load_model_config()
        self.assertEqual(config["api_key"], "file-secret")
        self.assertEqual(config["base_url"], "https://api.deepseek.com")

    def test_empty_file_preserves_local_model_environment(self):
        self.write("")
        with patch.dict("os.environ", {"AGENT_BASE_URL": "http://localhost:8000/v1", "AGENT_MODEL": "local-model"}):
            client = ModelClient()
        self.assertEqual(client.base, "http://localhost:8000/v1")
        self.assertEqual(client.key, "")

    def test_empty_key_has_clear_error(self):
        self.write("")
        with self.assertRaises(DemoError) as caught:
            ModelClient()
        self.assertEqual(caught.exception.code, "MODEL_NOT_CONFIGURED")
        self.assertIn("deepseek_config.json", str(caught.exception))

    def test_malformed_json_does_not_expose_secret(self):
        self.path.write_text('{"api_key": "private-test-secret",}', encoding="utf-8")
        with self.assertRaises(DemoError) as caught:
            load_model_config()
        self.assertEqual(caught.exception.code, "INVALID_CONFIG")
        self.assertNotIn("private-test-secret", str(caught.exception))

    def test_invalid_type_is_rejected(self):
        self.path.write_text('{"api_key": 123}', encoding="utf-8")
        with self.assertRaises(DemoError):
            load_model_config()
