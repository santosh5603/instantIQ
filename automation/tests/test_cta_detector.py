import unittest
import sys
import os

# Ensure parent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright_custom.utils.cta_detector import detect_cta

class TestCTADetector(unittest.TestCase):
    def test_comment_only_simple(self):
        caption = "Comment GUIDE to get my ultimate automation toolkit!"
        res = detect_cta(caption)
        self.assertTrue(res["requires_comment"])
        self.assertEqual(res["comment_keyword"], "GUIDE")
        self.assertFalse(res["requires_follow"])
        self.assertGreater(res["confidence"], 0.4)

    def test_comment_quoted_caps(self):
        caption = "Leave a comment with the word 'AI' to fetch direct Notion files."
        res = detect_cta(caption)
        self.assertTrue(res["requires_comment"])
        self.assertEqual(res["comment_keyword"], "AI")
        self.assertFalse(res["requires_follow"])

    def test_follow_and_comment(self):
        caption = "Make sure you follow my profile + comment PDF and I will DM you the link."
        res = detect_cta(caption)
        self.assertTrue(res["requires_comment"])
        self.assertEqual(res["comment_keyword"], "PDF")
        self.assertTrue(res["requires_follow"])
        self.assertGreaterEqual(res["confidence"], 0.8)

    def test_direct_dm_trigger(self):
        caption = "Send me a DM with START to begin learning Python."
        res = detect_cta(caption)
        self.assertTrue(res["requires_dm"])
        self.assertEqual(res["dm_keyword"], "START")
        self.assertFalse(res["requires_comment"])

    def test_no_cta_caption(self):
        caption = "Just had an amazing coffee today and worked on my next-gen SaaS architecture. Coffee vibes only."
        res = detect_cta(caption)
        self.assertFalse(res["requires_comment"])
        self.assertFalse(res["requires_follow"])
        self.assertFalse(res["requires_dm"])
        self.assertIsNone(res["comment_keyword"])
        self.assertEqual(res["confidence"], 0.0)

if __name__ == "__main__":
    unittest.main()
