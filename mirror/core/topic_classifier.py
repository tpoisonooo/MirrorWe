"""
Topic classification for group messages using LLM
"""

import hashlib
import json
import os
from typing import Dict, List, Optional, Tuple

from loguru import logger

from ..primitive import LLM
from ..wechat.message import Message
from .topic import Topic


class TopicClassifier:
    """
    Classifies group messages into different topics using LLM.
    """
    
    def __init__(self):
        self.llm = LLM()
        self.system_prompt = """
"""
    
    async def classify_message(self, message: Message, recent_topics: List[Topic], 
                             recent_messages: List[Dict]) -> Tuple[str, str, float]:
        """
        Classify a message into a topic.
        
        Args:
            message: The message to classify
            recent_topics: List of existing topics
            recent_messages: Recent messages for context
            
        Returns:
            Tuple of (topic_id, topic_name, confidence)
        """
        try:
            # Build context from recent messages
            context = self._build_context(recent_messages, recent_topics)
            
            # Create classification prompt
            prompt = self._create_classification_prompt(message, context, recent_topics)
            
            # Get LLM response
            response = await self.llm.generate_async(prompt, system_prompt=self.system_prompt)
            
            # Parse response
            result = self._parse_llm_response(response)
            
            if result and result.get('confidence', 0) > 0.6:
                return result['topic_id'], result['topic_name'], result['confidence']
            else:
                # Create new topic if confidence is low
                topic_name = self._generate_topic_name(message)
                topic_id = self._generate_topic_id(topic_name, message.group_id)
                return topic_id, topic_name, 0.7
                
        except Exception as e:
            logger.error(f"Error classifying message: {e}")
            # Fallback: create a new topic based on message content
            topic_name = self._generate_topic_name(message)
            topic_id = self._generate_topic_id(topic_name, message.group_id)
            return topic_id, topic_name, 0.5
    
    def _build_context(self, recent_messages: List[Dict], recent_topics: List[Topic]) -> str:
        """Build context from recent messages and topics."""
        context_parts = []
        
        # Add recent topics info
        if recent_topics:
            context_parts.append("Recent topics:")
            for topic in recent_topics[:5]:  # Limit to 5 most recent topics
                context_parts.append(f"- {topic.name} (ID: {topic.topic_id})")
        
        # Add recent messages for conversation flow
        if recent_messages:
            context_parts.append("\nRecent messages:")
            for msg in recent_messages[-10:]:  # Last 10 messages
                sender = msg.get('person_id', 'Unknown')
                content = msg.get('content', '')[:100]  # Truncate long messages
                context_parts.append(f"[{sender}]: {content}")
        
        return '\n'.join(context_parts)
    
    def _create_classification_prompt(self, message: Message, context: str, 
                                    recent_topics: List[Topic]) -> str:
        """Create the classification prompt for the LLM."""
        prompt = f"""
Context:
{context}

New message to classify:
Sender: {message.sender}
Content: {message.content}
Message Type: {message._type}

Based on the context and content of this message, determine which topic it belongs to.
If it doesn't fit well with existing topics, suggest a new topic name.

Available topics:
"""
        
        # Add existing topics
        if recent_topics:
            for topic in recent_topics:
                prompt += f"- {topic.name} (ID: {topic.topic_id})\n"
        else:
            prompt += "No existing topics\n"
        
        prompt += """

Provide your classification in JSON format with topic_name, topic_id, confidence, and reason."""
        
        return prompt
    
    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """Parse the LLM response to extract topic information."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            if '```json' in response:
                # Extract JSON from code block
                json_start = response.find('```json') + 7
                json_end = response.find('```', json_start)
                if json_end != -1:
                    response = response[json_start:json_end]
            elif '```' in response:
                # Extract from single code block
                json_start = response.find('```') + 3
                json_end = response.find('```', json_start)
                if json_end != -1:
                    response = response[json_start:json_end]
            
            result = json.loads(response)
            
            # Validate required fields
            required_fields = ['topic_name', 'topic_id', 'confidence', 'reason']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing required field in LLM response: {field}")
                    return None
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            return None
    
    def _generate_topic_name(self, message: Message) -> str:
        """Generate a topic name based on message content."""
        content = message.content.lower()
        
        # Simple keyword-based topic naming
        if any(word in content for word in ['项目', 'project', '任务', 'task']):
            return '项目讨论'
        elif any(word in content for word in ['技术', 'tech', '开发', 'dev', '代码', 'code']):
            return '技术交流'
        elif any(word in content for word in ['问题', 'question', '帮助', 'help', '求助']):
            return '问题求助'
        elif any(word in content for word in ['分享', 'share', '推荐', 'recommend']):
            return '分享推荐'
        elif any(word in content for word in ['闲聊', 'chat', '八卦', 'gossip']):
            return '闲聊八卦'
        else:
            # Use first few words of message as topic name
            words = message.content.split()[:3]
            if words:
                return ' '.join(words)
            else:
                return '未分类话题'
    
    def _generate_topic_id(self, topic_name: str, group_id: str) -> str:
        """Generate a unique topic ID based on topic name and group ID."""
        # Create a hash of topic name + group_id + timestamp for uniqueness
        import time
        content = f"{topic_name}_{group_id}_{int(time.time())}"
        return hashlib.md5(content.encode()).hexdigest()[:12]