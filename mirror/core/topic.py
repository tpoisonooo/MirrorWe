"""
Topic management for group conversations
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from ..primitive import safe_write_text, try_load_text
from ..wechat.message import Message
from .inner import Inner
from .memory import MemoryStream

class Topic:
    """
    Represents a conversation topic within a group chat.
    Manages messages and memory specific to this topic.
    """
    
    def __init__(self, topic_id: str, name: str, group_id: str):
        """
        Initialize a topic.
        
        Args:
            topic_id: Unique identifier for the topic
            name: Human-readable name for the topic
            group_id: ID of the parent group
        """
        self.name = name
        self.group_id = group_id
        self.memory = MemoryStream()
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        
    async def add_message(self, message: Message, person_id: str) -> None:
        """
        Add a message to this topic.
        
        Args:
            message: The message to add
            person_id: ID of the person who sent the message
        """
        # Convert message to Inner format for memory storage
        inner = Inner(
            role="user" if person_id != message.sender_id else "assistant",
            content=message.content,
            ts=datetime.now(),
            person=person_id
        )
        
        self.memory.add(group=inner)
        self.last_updated = datetime.now()
        
    def get_recent_messages(self, limit: int = 20) -> List[Dict]:
        """Get recent messages from this topic."""
        return self.memory.group[-limit:] if self.memory.group else []
    
    def to_dict(self) -> Dict:
        """Convert topic to dictionary representation."""
        return {
            'topic_id': self.topic_id,
            'name': self.name,
            'group_id': self.group_id,
            'message_count': len(self.memory.group),
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'summary': self.get_summary()
        }