"""  
Comet-Style AI Agent Brain
Handles task understanding, planning, and tool orchestration
"""

import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import openai
from loguru import logger


class ToolType(Enum):
    BROWSER_NAVIGATE = "browser_navigate"
    BROWSER_CLICK = "browser_click"
    BROWSER_TYPE = "browser_type"
    BROWSER_SCREENSHOT = "browser_screenshot"
    MAC_OPEN_APP = "mac_open_app"
    MAC_CLOSE_APP = "mac_close_app"
    MAC_TYPE_TEXT = "mac_type_text"
    MAC_PRESS_KEY = "mac_press_key"
    SEND_MESSAGE = "send_message"
    WAIT = "wait"


@dataclass
class Tool:
    name: str
    type: ToolType
    parameters: Dict[str, Any]
    description: str


@dataclass
class Task:
    id: str
    description: str
    status: str  # pending, in_progress, completed, failed
    steps: List[Tool]
    result: Optional[str] = None


class CometAgent:
    """
    Agent that mimics Comet's approach:
    1. Understand the user's voice command
    2. Break it down into executable steps (tools)
    3. Execute each step in sequence
    4. Handle errors and adapt
    5. Report back via voice
    """
    
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.conversation_history: List[Dict] = []
        self.current_task: Optional[Task] = None
        
        # Available tools definition for the LLM
        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "browser_navigate",
                    "description": "Navigate to a URL in the browser",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "The URL to navigate to"},
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_click",
                    "description": "Click an element on the page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector or description of element"},
                        },
                        "required": ["selector"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_type",
                    "description": "Type text into an input field",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "selector": {"type": "string", "description": "CSS selector of input field"},
                            "text": {"type": "string", "description": "Text to type"},
                        },
                        "required": ["selector", "text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mac_open_app",
                    "description": "Open a macOS application",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {"type": "string", "description": "Name of the app (e.g., 'Chrome', 'VS Code', 'WhatsApp')"},
                        },
                        "required": ["app_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mac_type_text",
                    "description": "Type text in the currently focused Mac application",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Text to type"},
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "send_message",
                    "description": "Send a message via an messaging app",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app": {"type": "string", "description": "Messaging app (iMessage, WhatsApp, Telegram, etc.)"},
                            "recipient": {"type": "string", "description": "Name or number of recipient"},
                            "message": {"type": "string", "description": "Message content"},
                        },
                        "required": ["app", "recipient", "message"]
                    }
                }
            },
        ]
    
    async def process_voice_command(self, command: str) -> Task:
        """
        Main entry point: takes a voice command and converts it to a task plan
        """
        logger.info(f"Processing voice command: {command}")
        
        # Add user command to conversation
        self.conversation_history.append({
            "role": "user",
            "content": command
        })
        
        # Create system prompt that guides the agent to think like Comet
        system_prompt = """You are a voice-controlled Mac assistant that executes tasks like Comet.
        
        Your capabilities:
        - Open and control Mac applications
        - Navigate websites and interact with them
        - Type text and send messages
        - Execute multi-step workflows
        
        When given a command, break it down into specific tool calls.
        Think step-by-step and use the available tools to accomplish the task.
        Be proactive and handle common scenarios intelligently.
        
        Examples:
        - "Open Chrome and go to TikTok" -> mac_open_app(Chrome) + browser_navigate(tiktok.com)
        - "Send 'hey' to John on WhatsApp" -> mac_open_app(WhatsApp) + send_message(...)
        - "Type my email address" -> mac_type_text(user@email.com)
        """
        
        messages = [
            {"role": "system", "content": system_prompt}
        ] + self.conversation_history
        
        # Call LLM with tool calling enabled
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            tools=self.tools_schema,
            tool_choice="auto"
        )
        
        # Extract tool calls and create task
        message = response.choices[0].message
        
        if message.tool_calls:
            # Convert tool calls to Task
            steps = []
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                func_args = json.loads(tool_call.function.arguments)
                
                tool = Tool(
                    name=func_name,
                    type=ToolType(func_name),
                    parameters=func_args,
                    description=f"Execute {func_name} with {func_args}"
                )
                steps.append(tool)
            
            task = Task(
                id=f"task_{len(self.conversation_history)}",
                description=command,
                status="pending",
                steps=steps
            )
            
            self.current_task = task
            logger.info(f"Created task with {len(steps)} steps")
            return task
        
        else:
            # No tools needed, just respond
            logger.info("No tools needed for this command")
            return Task(
                id=f"task_{len(self.conversation_history)}",
                description=command,
                status="completed",
                steps=[],
                result=message.content
            )
    
    def get_task_status(self) -> Optional[Dict]:
        """Get current task execution status"""
        if self.current_task:
            return {
                "id": self.current_task.id,
                "description": self.current_task.description,
                "status": self.current_task.status,
                "steps_total": len(self.current_task.steps),
                "result": self.current_task.result
            }
        return None