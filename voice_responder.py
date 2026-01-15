"""
Voice Responder - Converts text responses to speech output
Provides voice feedback to the user
"""

import pyttsx3
from loguru import logger
import threading
import queue
from typing import Optional

class VoiceResponder:
    """
    Handles text-to-speech output
    - Converts text responses to voice
    - Manages voice queue for multiple responses
    - Provides customizable voice settings
    """
    
    def __init__(self, rate: int = 175, volume: float = 1.0, voice_id: Optional[int] = None):
        """
        Initialize voice responder
        
        Args:
            rate: Speech rate (words per minute, default 175)
            volume: Volume level (0.0 to 1.0, default 1.0)
            voice_id: Voice ID to use (None for system default)
        """
        self.engine = pyttsx3.init()
        self.response_queue = queue.Queue()
        self.is_speaking = False
        self.speak_thread = None
        
        # Configure voice settings
        self.engine.setProperty('rate', rate)
        self.engine.setProperty('volume', volume)
        
        # Set voice if specified
        if voice_id is not None:
            voices = self.engine.getProperty('voices')
            if voice_id < len(voices):
                self.engine.setProperty('voice', voices[voice_id].id)
        
        logger.info("Voice responder initialized")
    
    def speak(self, text: str, blocking: bool = False):
        """
        Speak the given text
        
        Args:
            text: Text to speak
            blocking: If True, waits until speech is complete
        """
        logger.info(f"Speaking: {text}")
        
        if blocking:
            # Speak immediately and wait
            self.engine.say(text)
            self.engine.runAndWait()
        else:
            # Add to queue for async speaking
            self.response_queue.put(text)
            
            # Start speaking thread if not already running
            if not self.is_speaking:
                self._start_speak_thread()
    
    def _start_speak_thread(self):
        """
        Start background thread for async speaking
        """
        self.is_speaking = True
        self.speak_thread = threading.Thread(target=self._speak_loop, daemon=True)
        self.speak_thread.start()
    
    def _speak_loop(self):
        """
        Main speaking loop - processes queued responses
        """
        while self.is_speaking:
            try:
                # Get next text from queue (with timeout)
                text = self.response_queue.get(timeout=1)
                
                # Speak it
                self.engine.say(text)
                self.engine.runAndWait()
                
            except queue.Empty:
                # No more items in queue, stop thread
                self.is_speaking = False
            except Exception as e:
                logger.error(f"Error in speak loop: {e}")
    
    def speak_confirmation(self):
        """
        Speak a quick confirmation sound/word
        """
        self.speak("OK", blocking=True)
    
    def speak_error(self, error_msg: Optional[str] = None):
        """
        Speak an error message
        """
        if error_msg:
            self.speak(f"Error: {error_msg}")
        else:
            self.speak("Sorry, I encountered an error")
    
    def speak_task_complete(self, task_description: Optional[str] = None):
        """
        Announce task completion
        """
        if task_description:
            self.speak(f"Done. {task_description}")
        else:
            self.speak("Task completed")
    
    def speak_task_status(self, status: str):
        """
        Announce task status
        """
        self.speak(status)
    
    def stop(self):
        """
        Stop speaking and clear queue
        """
        self.is_speaking = False
        
        # Clear queue
        while not self.response_queue.empty():
            try:
                self.response_queue.get_nowait()
            except queue.Empty:
                break
        
        # Stop current speech
        try:
            self.engine.stop()
        except Exception as e:
            logger.error(f"Error stopping speech: {e}")
        
        logger.info("Voice responder stopped")
    
    def list_voices(self):
        """
        List available voices
        """
        voices = self.engine.getProperty('voices')
        for i, voice in enumerate(voices):
            print(f"{i}: {voice.name} - {voice.languages}")
    
    def set_voice(self, voice_id: int):
        """
        Change voice
        """
        voices = self.engine.getProperty('voices')
        if voice_id < len(voices):
            self.engine.setProperty('voice', voices[voice_id].id)
            logger.info(f"Voice changed to: {voices[voice_id].name}")
        else:
            logger.warning(f"Invalid voice ID: {voice_id}")
    
    def set_rate(self, rate: int):
        """
        Change speech rate
        """
        self.engine.setProperty('rate', rate)
        logger.info(f"Speech rate set to: {rate}")
    
    def set_volume(self, volume: float):
        """
        Change volume (0.0 to 1.0)
        """
        self.engine.setProperty('volume', volume)
        logger.info(f"Volume set to: {volume}")

# Example usage
if __name__ == "__main__":
    responder = VoiceResponder()
    
    # List available voices
    print("Available voices:")
    responder.list_voices()
    
    # Test speaking
    responder.speak("Hello! I am your voice assistant.", blocking=True)
    responder.speak("I can help you with various tasks on your Mac.", blocking=True)
    
    # Test async speaking
    responder.speak("This is an async message")
    responder.speak("And another one")
    
    import time
    time.sleep(5)  # Wait for async messages to complete
    
    responder.stop()
