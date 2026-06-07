class QueueNames:
    REEL         = "reelise:reel_queue"
    COMMENT      = "reelise:comment_queue"
    RESOURCE     = "reelise:resource_queue"
    NOTION_SYNC  = "reelise:notion_sync_queue"
    RETRY        = "reelise:retry_queue"
    DEAD_LETTER  = "reelise:dead_letter_queue"

# Global constant aliases for compatibility with routers/health.py and routers/analytics.py
REELS_QUEUE = QueueNames.REEL
NOTION_SYNC_QUEUE = QueueNames.NOTION_SYNC
DEAD_LETTER_QUEUE = QueueNames.DEAD_LETTER
