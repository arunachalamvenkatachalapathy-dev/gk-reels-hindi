"""Gate tests for the Hindi Drive-stock publisher. No network, no credentials."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import stock_publish as sp

CONFIG = {
    "drive_root_folder_id": "root",
    "channel_id": "UCpvGKLB9EVeJgYzVjkEZdqQ",
    "slots": {"morning": "07:30", "afternoon": "19:30"},
    "window_minutes": 120,
    "skip_qid_range_end": 88,
    "state_branch": "hi-stock-publication-state",
    "state_file": "stock_state.json",
}


def ist(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc) - timedelta(hours=5, minutes=30)


class ManifestName(unittest.TestCase):
    def test_manifest(self):
        self.assertEqual(sp.parse_manifest_name("q0131_seo_manifest.json"), "q0131")

    def test_foreign_rejected(self):
        self.assertIsNone(sp.parse_manifest_name("q0131.mp4"))
        self.assertIsNone(sp.parse_manifest_name("plan.pdf"))


class CandidateChoice(unittest.TestCase):
    def test_range_and_order(self):
        stock = [{"name": "q0200_seo_manifest.json"}, {"name": "q0050_seo_manifest.json"}, {"name": "q0089_seo_manifest.json"}]
        out = sp.manifest_candidates(stock, CONFIG)
        self.assertEqual([q for q, _ in out], ["q0089", "q0200"])


class SlotGate(unittest.TestCase):
    def test_morning_open(self):
        slot = sp.select_slot(ist(2026, 11, 2, 7, 45), CONFIG, {"slots": {}})
        self.assertEqual(slot["key"], "2026-11-02:morning")

    def test_published_slot_not_repicked(self):
        state = {"slots": {"2026-11-02:morning": {"status": "published"}}}
        self.assertIsNone(sp.select_slot(ist(2026, 11, 2, 7, 45), CONFIG, state))

    def test_outside_window(self):
        self.assertIsNone(sp.select_slot(ist(2026, 11, 2, 12, 0), CONFIG, {"slots": {}}))


class _Resp:
    def __init__(self, status):
        self.status = status


class _HttpErr(Exception):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.resp = _Resp(status)


class _FlakyRequest:
    def __init__(self, failures, status):
        self.failures, self.status, self.calls = failures, status, 0

    def execute(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise _HttpErr(self.status)
        return {"items": []}


class ReadRetry(unittest.TestCase):
    def test_retries_transient_503_then_succeeds(self):
        req, waits = _FlakyRequest(2, 503), []
        self.assertEqual(sp.execute_read_with_retry(req, sleep=waits.append), {"items": []})
        self.assertEqual(req.calls, 3)
        self.assertEqual(waits, [2.0, 4.0])

    def test_gives_up_loudly_after_attempts(self):
        req = _FlakyRequest(99, 503)
        with self.assertRaises(_HttpErr):
            sp.execute_read_with_retry(req, attempts=3, sleep=lambda s: None)
        self.assertEqual(req.calls, 3)

    def test_non_transient_error_not_retried(self):
        req = _FlakyRequest(99, 403)
        with self.assertRaises(_HttpErr):
            sp.execute_read_with_retry(req, sleep=lambda s: None)
        self.assertEqual(req.calls, 1)


if __name__ == "__main__":
    unittest.main()
