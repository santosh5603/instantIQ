import sys
from unittest.mock import MagicMock
# Mock/Stub transitive pyiceberg dependency for supabase / storage3 compatibility on Python 3.14
sys.modules['pyiceberg'] = MagicMock()
sys.modules['pyiceberg.catalog'] = MagicMock()
sys.modules['pyiceberg.catalog.rest'] = MagicMock()

import unittest
from unittest.mock import AsyncMock, patch
import asyncio
import uuid
import os
from datetime import datetime

# Ensure local directories are prioritized in search path to avoid package shadowing
test_dir = os.path.dirname(os.path.abspath(__file__))
automation_dir = os.path.dirname(test_dir)
project_root = os.path.dirname(automation_dir)
backend_dir = os.path.join(project_root, "backend")

sys.path.insert(0, backend_dir)
sys.path.insert(0, automation_dir)
sys.path.insert(0, os.path.join(automation_dir, "workers"))

from workers.reel_worker import process_reel_task
from app.models.reel import Reel

class TestReelWorker(unittest.IsolatedAsyncioTestCase):
    @patch("workers.reel_worker.get_worker_db")
    @patch("workers.reel_worker.async_playwright")
    @patch("workers.reel_worker.is_session_valid")
    @patch("workers.reel_worker.extract_reel_metadata")
    @patch("workers.reel_worker.follow_creator")
    @patch("workers.reel_worker.post_comment")
    @patch("workers.reel_worker.open_creator_chat")
    @patch("workers.reel_worker.harvest_dm_responses")
    @patch("workers.reel_worker.redis_client")
    async def test_process_reel_task_success(
        self,
        mock_redis,
        mock_harvest_dms,
        mock_open_chat,
        mock_post_comment,
        mock_follow_creator,
        mock_extract_metadata,
        mock_is_session_valid,
        mock_playwright,
        mock_get_db
    ):
        # 1. Setup mock DB Session
        mock_session = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_session

        # Create mock Reel object
        reel_id = str(uuid.uuid4())
        mock_reel = Reel(
            id=uuid.UUID(reel_id),
            reel_url="https://www.instagram.com/reel/C3M8WnKvyBf/",
            status="pending"
        )

        # Mock database execute results depending on the select statement target
        def execute_side_effect(stmt, *args, **kwargs):
            stmt_str = str(stmt).lower()
            res = MagicMock()
            if "creator_relationships" in stmt_str:
                res.scalar_one_or_none.return_value = None
            else:
                res.scalar_one_or_none.return_value = mock_reel
            return res
        mock_session.execute.side_effect = execute_side_effect

        # 2. Setup Playwright mocks
        mock_page = AsyncMock()
        mock_context = AsyncMock()
        mock_context.new_page.return_value = mock_page
        
        mock_browser = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        
        mock_p_instance = AsyncMock()
        mock_p_instance.chromium.launch.return_value = mock_browser
        
        mock_playwright.return_value.__aenter__.return_value = mock_p_instance

        # 3. Setup behavior of scraper modules
        mock_is_session_valid.return_value = True
        mock_extract_metadata.return_value = ("creator_ninja", "Follow me + comment 'GUIDE' to receive the ultimate PDF now!")
        mock_follow_creator.return_value = True
        mock_post_comment.return_value = True
        mock_open_chat.return_value = True
        mock_harvest_dms.return_value = [
            {
                "resource_type": "pdf",
                "resource_url": "https://supabase.co/storage/v1/object/public/reelise-resources/ninja_guide.pdf",
                "resource_text": "Here is your requested guide!",
                "category": "Programming",
                "file_name": "ninja_guide.pdf"
            }
        ]

        # 4. Prepare job input data
        job_data = {
            "reel_id": reel_id,
            "payload": {
                "reel_url": "https://www.instagram.com/reel/C3M8WnKvyBf/"
            }
        }

        # 5. Run the worker pipeline
        await process_reel_task(job_data)

        # 6. Verify assertions on mock reel status transitions
        self.assertEqual(mock_reel.status, "completed")
        self.assertEqual(mock_reel.creator_name, "creator_ninja")
        self.assertTrue(mock_reel.requires_comment)
        self.assertTrue(mock_reel.requires_follow)
        self.assertEqual(mock_reel.comment_keyword, "GUIDE")
        self.assertTrue(mock_reel.commented)
        self.assertTrue(mock_reel.followed)
        self.assertIsNotNone(mock_reel.processed_at)

        # Verify Redis push was triggered for Notion sync
        mock_redis.lpush.assert_called_once()
        args, kwargs = mock_redis.lpush.call_args
        self.assertEqual(args[0], "reelise:notion_sync_queue")

        # Verify database commits were performed
        self.assertGreater(mock_session.commit.call_count, 0)

if __name__ == "__main__":
    unittest.main()
