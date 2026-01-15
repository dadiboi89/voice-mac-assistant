#!/usr/bin/env python3
"""
Main orchestrator for the voice-controlled Mac assistant.

Coordinates:
- VoiceListener: captures wake word + commands from mic
- CometAgent: plans actions using the OpenAI API
- ToolExecutor: executes Mac/browser automation tools
- VoiceResponder: speaks responses back to you
"""

import os
import asyncio
import sys
from typing import Optional

from loguru import logger

from voice_listener import VoiceListener
from voice_responder import VoiceResponder
from agent import CometAgent
from tools_executor import ToolExecutor


class VoiceAssistant:
    """Main orchestrator that coordinates all components."""

    def __init__(self, openai_api_key: str, wake_word: str = "hey assistant") -> None:
        """
        Initialize the voice assistant.

        Args:
            openai_api_key: OpenAI API key for agent brain.
            wake_word: Wake word to activate assistant.
        """
        logger.info("Initializing Voice-Controlled Mac Assistant...")

        # Core components
        self.listener = VoiceListener(
            wake_word=wake_word,
            callback=self._on_command,
        )
        self.responder = VoiceResponder()
        self.agent = CometAgent(api_key=openai_api_key)
        self.executor = ToolExecutor()

        self.is_running: bool = False

        logger.info("Voice Assistant initialized successfully")

    def start(self) -> None:
        """Start the voice assistant."""
        logger.info("Starting Voice Assistant...")
        self.is_running = True

        # Start voice listener in background
        self.listener.start()

        # Greet user
        self.responder.speak(
            "Voice assistant activated. I'm ready to help.",
            blocking=True,
        )

        logger.info("Voice Assistant is now running")

    def stop(self) -> None:
        """Stop the voice assistant and clean up resources."""
        logger.info("Stopping Voice Assistant...")
        self.is_running = False

        # Stop all components
        self.listener.stop()
        self.responder.speak(
            "Voice assistant shutting down. Goodbye!",
            blocking=True,
        )
        self.responder.stop()

        # Cleanup executor (async)
        asyncio.run(self.executor.cleanup())

        logger.info("Voice Assistant stopped")

    def _run_async(self, coro: asyncio.Future) -> None:
        """
        Safely run an async coroutine from sync context.

        Ensures a running event loop is available whether started from
        CLI or an environment that already has a loop.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(coro)
        else:
            loop.create_task(coro)

    def _on_command(self, command: str) -> None:
        """
        Callback when a voice command is received.

        Pipeline:
        1. Acknowledge user.
        2. Ask agent to plan tools.
        3. Execute planned tools.
        4. Speak back summary/result.
        """
        logger.info(f"Processing command: {command!r}")

        # Quick acknowledgement
        self.responder.speak("Working on it.", blocking=False)

        async def handle_command() -> None:
            try:
                # 1. Get plan from agent (tool calls)
                logger.debug("Sending command to agent for planning...")
                plan = await self.agent.plan_actions(command)
                logger.debug(f"Received plan from agent: {plan}")

                # 2. Execute tools
                logger.debug("Executing planned tools...")
                result_summary = await self.executor.execute_plan(plan)
                logger.debug(f"Execution summary: {result_summary}")

                # 3. Speak back the result
                spoken = result_summary or "Task completed."
                self.responder.speak(spoken, blocking=False)

            except Exception as e:
                logger.exception("Error while handling command")
                self.responder.speak(
                    f"Sorry, something went wrong while handling your request: {e}",
                    blocking=False,
                )

        # Run async handler
        self._run_async(handle_command())


def _get_api_key() -> str:
    """
    Retrieve the OpenAI API key from environment variables.

    Exits with a clear error message if not set.
    """
    api_key: Optional[str] = os.getenv("OPENAI_API_KEY")

    if not api_key:
        logger.error(
            "OPENAI_API_KEY is not set.\n"
            "Please create a .env file locally (NOT committed to Git) or export "
            "OPENAI_API_KEY in your shell before running this script."
        )
        sys.exit(1)

    return api_key


def main() -> None:
    """Entry point for running the assistant from the command line."""
    logger.info("Starting Voice Mac Assistant entrypoint...")

    api_key = _get_api_key()

    assistant = VoiceAssistant(
        openai_api_key=api_key,
        wake_word="hey assistant",
    )

    try:
        assistant.start()
        # Keep the main thread alive while listener runs in background.
        # The listener implementation should manage its own loop/thread.
        logger.info("Press Ctrl+C to stop the assistant.")
        while assistant.is_running:
            # Simple keep-alive loop
            asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down.")
    finally:
        assistant.stop()


if __name__ == "__main__":
    main()
