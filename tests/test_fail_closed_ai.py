"""Offline regression tests for Hindi AI failure handling; never contacts providers."""
import importlib.util
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

ai = load_module("fail_closed_ai_engine", SCRIPTS / "ai_engine.py")

class MockResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload
    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

class AIEngineFailClosedTests(unittest.TestCase):
    def setUp(self):
        self.original_key = ai.OPENROUTER_API_KEY
        ai.OPENROUTER_API_KEY = "test-key"
    def tearDown(self):
        ai.OPENROUTER_API_KEY = self.original_key
    def test_missing_key_fails_without_request(self):
        ai.OPENROUTER_API_KEY = ""
        with patch.object(ai.requests, "post") as post, self.assertRaisesRegex(RuntimeError, "key is missing"):
            ai.call_openrouter("test prompt")
        post.assert_not_called()
    def test_transport_error_stops_after_one_request(self):
        with patch.object(ai.requests, "post", side_effect=OSError("offline")) as post, self.assertRaisesRegex(RuntimeError, "request failed"):
            ai.call_openrouter("test prompt")
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["json"]["model"], ai.OPENROUTER_MODEL)
    def test_http_error_stops_without_retry(self):
        with patch.object(ai.requests, "post", return_value=MockResponse(402, {})) as post, self.assertRaisesRegex(RuntimeError, "HTTP 402"):
            ai.call_openrouter("test prompt")
        post.assert_called_once()
    def test_response_parse_error_stops(self):
        with patch.object(ai.requests, "post", return_value=MockResponse(200, ValueError("bad response"))) as post, self.assertRaisesRegex(RuntimeError, "invalid JSON"):
            ai.call_openrouter("test prompt")
        post.assert_called_once()
    def test_malformed_model_json_stops(self):
        response = MockResponse(200, {"choices": [{"message": {"content": "not json"}}]})
        with patch.object(ai.requests, "post", return_value=response) as post, self.assertRaisesRegex(RuntimeError, "invalid JSON"):
            ai.call_openrouter("test prompt")
        post.assert_called_once()
    def test_incomplete_model_package_stops(self):
        response = MockResponse(200, {"choices": [{"message": {"content": json.dumps({"title": "title only"})}}]})
        with patch.object(ai.requests, "post", return_value=response) as post, self.assertRaisesRegex(RuntimeError, "incomplete package"):
            ai.call_openrouter("test prompt")
        post.assert_called_once()
    def test_success_uses_single_configured_model(self):
        expected = {"title": "title", "viral_hook": "hook"}
        response = MockResponse(200, {"choices": [{"message": {"content": json.dumps(expected)}}]})
        with patch.object(ai.requests, "post", return_value=response) as post:
            self.assertEqual(ai.call_openrouter("test prompt"), expected)
        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["json"]["model"], ai.OPENROUTER_MODEL)

# Stub render/provider-dependent imports before loading pipeline.
render_calls = []
render_stub = types.ModuleType("render")
render_stub.REVIEWED = {"q1": {}}
render_stub.render_video = lambda *args, **kwargs: render_calls.append((args, kwargs))
old_render = sys.modules.get("render")
sys.modules["render"] = render_stub
pipeline = load_module("fail_closed_pipeline", SCRIPTS / "run_pipeline.py")
if old_render is None:
    sys.modules.pop("render", None)
else:
    sys.modules["render"] = old_render

class PipelineFailClosedTests(unittest.TestCase):
    def setUp(self):
        render_calls.clear()
        self.question = {"id": "q1", "question": "What is it?", "options": ["A", "B"], "answer": "A"}
        self.state = {"published_ids": [], "current_day": 1, "total_published": 0, "videos_per_day": 2}
    def run_pipeline(self, seo_result, enable_youtube=True):
        if isinstance(seo_result, Exception):
            def generate(*args, **kwargs):
                raise seo_result
        else:
            def generate(*args, **kwargs):
                return seo_result
        seo_stub = types.SimpleNamespace(
            detect_topic_hi=lambda question: ("topic", [], []),
            generate_seo_hi=generate,
        )
        modules = {"render": render_stub, "seo_agent": seo_stub,
                   "upload_telegram": types.SimpleNamespace(send_telegram_update=lambda *a, **k: False)}
        if enable_youtube:
            modules["upload_youtube"] = types.SimpleNamespace(
                upload_short=lambda *a, **k: "mock-video-id",
                get_youtube_client=lambda: None,
            )
        env = {"IG_ACCESS_TOKEN": "", "IG_USER_ID": "", "GITHUB_TOKEN": "", "GITHUB_REPOSITORY": ""}
        if enable_youtube:
            env.update({key: "test" for key in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")})
        fake_now = pipeline.datetime.datetime(2026, 10, 24, 20, 0, tzinfo=pipeline.IST)
        with patch.object(pipeline, "load_json", side_effect=[[self.question], self.state]), \
             patch.object(pipeline, "save_json"), \
             patch.object(pipeline, "get_ist_now", return_value=fake_now), \
             patch.object(pipeline, "get_slot_track", return_value="track"), \
             patch.object(pipeline, "OUT_DIR", str(ROOT / "fake-output")), \
             patch.dict(sys.modules, modules), \
             patch.dict(os.environ, env, clear=True), \
             patch.object(pipeline.sys, "argv", ["run_pipeline.py"]):
            pipeline.main()
    def test_model_error_stops_before_render_or_upload(self):
        with self.assertRaisesRegex(RuntimeError, "metadata generation failed"):
            self.run_pipeline(RuntimeError("mock model failure"))
        self.assertEqual(render_calls, [])
        self.assertEqual(self.state["published_ids"], [])
    def test_empty_seo_stops_before_render_or_upload(self):
        with self.assertRaisesRegex(RuntimeError, "metadata generation failed"):
            self.run_pipeline(None)
        self.assertEqual(render_calls, [])
        self.assertEqual(self.state["published_ids"], [])
    def test_valid_seo_reaches_render_and_successful_mock_upload(self):
        valid = {"topic": "topic", "title": "title", "description": "caption", "tags": ["tag"],
                 "ig_caption": "caption", "fb_caption": "caption"}
        self.run_pipeline(valid)
        self.assertEqual(len(render_calls), 1)
        self.assertEqual(self.state["published_ids"], ["q1"])
        self.assertEqual(self.state["total_published"], 1)

if __name__ == "__main__":
    unittest.main()
