import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from notion_client import AsyncClient
from app.config import settings
from app.models.reel import Reel
from app.models.dm_resource import DMResource

logger = logging.getLogger("notion_service")

class NotionService:
    def __init__(self):
        self.token = settings.NOTION_API_KEY
        self.db_id = settings.NOTION_RESOURCES_DB_ID
        
        if self.token and self.db_id and "dummy" not in self.token and "dummy" not in self.db_id:
            try:
                self.client = AsyncClient(auth=self.token)
                logger.info("Notion AsyncClient initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Notion AsyncClient: {str(e)}")
                self.client = None
        else:
            logger.warning("Notion API Key or DB ID is dummy. Notion operations will run in mock mode.")
            self.client = None

    def _get_resource_properties(self, reel: Reel, resource: DMResource) -> Dict[str, Any]:
        """
        Builds the standard Notion database properties object for a resource
        aligned with the actual Reelise Notion database schema.
        """
        # Determine Title
        title_text = resource.file_name or f"Resource from @{reel.creator_name or 'creator'}"
        if len(title_text) > 100:
            title_text = title_text[:97] + "..."

        # Truncate caption if present to stay under Notion's limit
        caption_snippet = reel.caption or ""
        if len(caption_snippet) > 2000:
            caption_snippet = caption_snippet[:1997] + "..."

        # Map categories to valid Notion options:
        # Tutorial, Marketing, Entertainment, Educational, Product Demo, Testimonial, Behind the Scenes, Announcement
        raw_category = resource.category or "Other"
        category_mapping = {
            "AI": "Educational",
            "Programming": "Educational",
            "Career": "Educational",
            "Fitness": "Educational",
            "Communication": "Educational",
            "Marketing": "Marketing",
            "Announcement": "Announcement",
            "Product Demo": "Product Demo",
            "Behind the Scenes": "Behind the Scenes",
            "Tutorial": "Tutorial",
            "Entertainment": "Entertainment",
            "Testimonial": "Testimonial"
        }
        category = category_mapping.get(raw_category, "Educational")

        # Map resource types to valid Notion options:
        # Video, Image, Article, Audio, Template, Document, Animation
        raw_type = (resource.resource_type or "document").lower()
        if "pdf" in raw_type or "doc" in raw_type or "xls" in raw_type or "ppt" in raw_type or "file" in raw_type:
            res_type = "Document"
        elif "link" in raw_type or "url" in raw_type or "http" in raw_type:
            res_type = "Article"
        elif "video" in raw_type or "mp4" in raw_type:
            res_type = "Video"
        elif "image" in raw_type or "png" in raw_type or "jpg" in raw_type:
            res_type = "Image"
        elif "audio" in raw_type or "mp3" in raw_type:
            res_type = "Audio"
        elif "template" in raw_type:
            res_type = "Template"
        elif "animation" in raw_type:
            res_type = "Animation"
        else:
            res_type = "Document"

        # Formulate Resource URL (direct download public link or DM text link)
        resource_url = resource.resource_url
        if not resource_url and resource.attachment_path:
            from app.services.supabase_service import supabase_service
            resource_url = f"{supabase_service.url}/storage/v1/object/public/{supabase_service.bucket_name}/{resource.attachment_path}"

        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title_text
                        }
                    }
                ]
            },
            "Caption": {
                "rich_text": [
                    {
                        "text": {
                            "content": caption_snippet
                        }
                    }
                ]
            },
            "Creator": {
                "rich_text": [
                    {
                        "text": {
                            "content": f"@{reel.creator_name}" if reel.creator_name else "Unknown"
                        }
                    }
                ]
            },
            "Category": {
                "select": {
                    "name": category
                }
            },
            "Resource Type": {
                "select": {
                    "name": res_type
                }
            },
            "URL": {
                "url": reel.reel_url
            },
            "Status": {
                "status": {
                    "name": "To Review"
                }
            },
            "Date Added": {
                "date": {
                    "start": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            }
        }

        if resource_url:
            properties["File Link"] = {
                "url": resource_url
            }

        return properties

    async def sync_resource(self, reel: Reel, resource: DMResource) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Creates or updates a resource entry in the Notion Database.
        
        Returns:
            Tuple[bool, notion_page_id, error_message]
        """
        if not self.client:
            logger.warning(f"[Mock] Syncing resource {resource.id} to Notion DB {self.db_id}")
            mock_page_id = f"mock-notion-page-{resource.id}"
            return True, mock_page_id, None

        try:
            properties = self._get_resource_properties(reel, resource)

            if resource.notion_page_id:
                # Update existing page
                logger.info(f"Updating Notion page {resource.notion_page_id} for resource {resource.id}")
                await self.client.pages.update(
                    page_id=resource.notion_page_id,
                    properties=properties
                )
                return True, resource.notion_page_id, None
            else:
                # Create new page
                logger.info(f"Creating new Notion page for resource {resource.id}")
                response = await self.client.pages.create(
                    parent={"database_id": self.db_id},
                    properties=properties
                )
                new_page_id = response.get("id")
                
                # Add block children with caption snippet if caption exists
                if reel.caption:
                    try:
                        await self.client.blocks.children.append(
                            block_id=new_page_id,
                            children=[
                                {
                                    "object": "block",
                                    "type": "heading_2",
                                    "heading_2": {
                                        "rich_text": [
                                            {"type": "text", "text": {"content": "Instagram Caption Extract"}}
                                        ]
                                    }
                                },
                                {
                                    "object": "block",
                                    "type": "paragraph",
                                    "paragraph": {
                                        "rich_text": [
                                            {"type": "text", "text": {"content": reel.caption[:2000]}}
                                        ]
                                    }
                                }
                            ]
                        )
                    except Exception as block_err:
                        logger.error(f"Failed to append caption blocks to Notion page: {str(block_err)}")
                
                return True, new_page_id, None

        except Exception as e:
            logger.error(f"Error syncing resource to Notion: {str(e)}")
            return False, None, str(e)

notion_service = NotionService()
