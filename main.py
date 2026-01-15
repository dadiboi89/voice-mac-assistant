#!/usr/bin/env python3
"""
Main Orchestrator - Voice-Controlled Mac Assistant
Ties together all components:
- Voice Listener (captures voice commands)
- Agent Brain (understands and plans tasks)
- Tool Executor (executes actions)
- Voice Responder (provides voice feedback)
"""

import os
import asyncio
import sys
from loguru import logger
from typing import Optional

# Import our modules
from voice_listener import VoiceListener
from voice_responder import VoiceResponder
from agent import CometAgent
from tools_executor import ToolExecutor

class VoiceAssistant:
    """
    Main orchestrator that coordinates all components
    """
    
    def __init__(self, openai_api_key: str, wake_word: str = "hey assistant"):
        """
        Initialize the voice assistant
        
        Args:
            openai_api_key: OpenAI API key for agent brain
            wake_word: Wake word to activate assistant
        """
        logger.info("Initializing Voice-Controlled Mac Assistant...")
        
        # Initialize components
        self.listener = VoiceListener(wake_word=wake_word, callback=self._on_command)
        self.responder = VoiceResponder()
        self.agent = CometAgent(api_key=openai_api_key)
        self.executor = ToolExecutor()
        
        self.is_running = False
        
        logger.info("Voice Assistant initialized successfully")
    
    def start(self):
        """
        Start the voice assistant
        """
        logger.info("Starting Voice Assistant...")
        self.is_running = True
        
        # Start voice listener
        self.listener.start()
        
        # Greet user
        self.responder.speak("Voice assistant activated. I'm ready to help.", blocking=True)
        
        logger.info("Voice Assistant is now running")
    
    def stop(self):
        """
        Stop the voice assistant
        """
        logger.info("Stopping Voice Assistant...")
        self.is_running = False
        
        # Stop all components
        self.listener.stop()
        self.responder.speak("Voice assistant shutting down. Goodbye!", blocking=True)
        self.responder.stop()
        
        # Cleanup
        asyncio.run(self.executor.cleanup())
        
        logger.info("Voice Assistant stopped")
    
    def _on_command(self, command: str):
        """
        Callback when voice command is received
        Processes the command through agent -> executor pipeline
        """
        logger.info(f"Processing command: {command}")
        
        # Acknowledge command
        self.responder.speak("Working on it", blocking=False)
        
        # Process command asynchronously
        asyncio.run(self._process_command_async(command))
    
    async def _process_command_async(self, command: str):
        """
        Async processing of command
        """
        try:
            # Step 1: Agent processes command and creates task plan
            logger.info("Agent processing command...")
            task = await self.agent.process_voice_command(command)
            
            if not task.steps:
                # No tools needed, just respond with result
                if task.result:
                    self.responder.speak(task.result)
                else:
                    self.responder.speak("I'm not sure how to help with that")
                return
            
            # Step 2: Execute each tool in the task plan
            logger.info(f"Executing {len(task.steps)} steps...")
            task.status = "in_progress"
            
            results = []
            for i, tool in enumerate(task.steps):
                logger.info(f"Step {i+1}/{len(task.steps)}: {tool.name}")
                
                # Execute tool
                result = await self.executor.execute_tool(tool.name, tool.parameters)
                results.append(result)
                
                # Check if tool execution failed
                if not result.get("success", False):
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Tool execution failed: {error_msg}")
                    self.responder.speak_error(error_msg)
                    task.status = "failed"
                    return
            
            # Step 3: All tools executed successfully
            task.status = "completed"
            logger.info("Task completed successfully")
            
            # Provide completion feedback
            self.responder.speak_task_complete(task.description)
            
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            self.responder.speak_error(f"Failed to process command: {str(e)}")
    
    def run(self):
        """
        Run the assistant (blocking)
        """
        self.start()
        
        try:
            # Keep running until interrupted
            while self.is_running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()

def main():
    """
    Main entry point
    """
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("assistant.log", rotation="10 MB", level="DEBUG")
    
    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        print("Error: Please set OPENAI_API_KEY environment variable")
        print("Example: export OPENAI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Create and run assistant
    assistant = VoiceAssistant(
        openai_api_key=api_key,
        wake_word="hey assistant"
    )
    
    print("="*60)
    print("Voice-Controlled Mac Assistant")
    print("="*60)
    print(f"Wake word: 'hey assistant'")
    print("Say commands like:")
    print("  - 'Hey assistant, open Chrome and go to TikTok'")
    print("  - 'Hey assistant, send a message to John on WhatsApp'")
    print("  - 'Hey assistant, type my email address'")
    print("")
    print("Press Ctrl+C to stop")
    print("="*60)
    print("")
    
    # Run the assistant
    assistant.run()

if __name__ == "__main__":
    main()
