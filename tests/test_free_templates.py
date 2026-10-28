"""Deterministic Hindi metadata template tests; no external provider calls."""
import importlib.util
import unittest
from unittest.mock import patch
from pathlib import Path

spec = importlib.util.spec_from_file_location("seo_free", Path(__file__).resolve().parents[1] / "scripts" / "seo_agent.py")
seo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seo)

class FreeTemplateTests(unittest.TestCase):
    def test_titles_are_deterministic_and_bounded(self):
        q = {"question": "सिंधु घाटी सभ्यता का कौन सा स्थल भारत में स्थित है?"}
        a = seo.format_smart_title_hi(q, 1, 1)
        b = seo.format_smart_title_hi(q, 1, 1)
        self.assertEqual(a, b)
        self.assertLessEqual(len(a[0]), 68)
        self.assertIn("#shorts", a[0])
    def test_generate_seo_does_not_call_provider(self):
        q = {"question": "सिंधु घाटी सभ्यता का कौन सा स्थल भारत में स्थित है?", "options": ["हड़प्पा", "मोहनजोदड़ो", "लोथल", "राखीगढ़ी"]}
        with patch.object(seo.requests, "post", side_effect=AssertionError("paid provider called")) as post:
            result = seo.generate_seo_hi(q, 1, 1)
            post.assert_not_called()
        self.assertIn("title", result)
        self.assertIn("description", result)
        self.assertIn("tags", result)
        self.assertEqual(result["viral_badge"], "आज का GK सवाल")
        self.assertEqual(result["pinned_comment"], "Comment your answer below.")

if __name__ == "__main__":
    unittest.main()
