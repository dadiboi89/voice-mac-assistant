"""
Voice Listener - Handles voice input capture and speech-to-text
Listens for wake word and converts voice commands to text
"""

import speech_recognition as sr
from loguru import logger
import threading
import queue
from typing import Optional, Callable
import time

class VoiceListener:
    """
    Continuously listens for voice commands
    - Detects wake word ("Hey Assistant" or similar)
    - Captures voice input
    - Converts to text using speech recognition
    - Passes text to callback function
    """
    
    def __init__(self, wake_word: str = "hey assistant", callback: Optional[Callable] = None):
        self.wake_word = wake_word.lower()
        self.callback = callback
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.command_queue = queue.Queue()
        self.listen_thread = None
        
        # Adjust for ambient noise
        logger.info("Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        logger.info("Microphone calibrated")
    
    def start(self):
        """
        Start listening for voice commands in background thread
        """
        if self.is_listening:
            logger.warning("Already listening")
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        logger.info(f"Voice listener started. Say '{self.wake_word}' to activate")
    
    def stop(self):
        """
        Stop listening
        """
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        logger.info("Voice listener stopped")
    
    def _listen_loop(self):
        """
        Main listening loop - runs in background thread
        """
        while self.is_listening:
            try:
                # Listen for audio
                with self.microphone as source:
                    logger.debug("Listening...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                # Convert to text
                text = self._recognize_speech(audio)
                
                if text:
                    logger.info(f"Heard: {text}")
                    
                    # Check for wake word
                    if self.wake_word in text.lower():
                        logger.info("Wake word detected!")
                        # Remove wake word from command
                        command = text.lower().replace(self.wake_word, "").strip()
                        
                        if command:
                            logger.info(f"Command: {command}")
                            self._process_command(command)
                        else:
                            # If no command after wake word, listen again for the actual command
                            self._wait_for_command()
            
            except sr.WaitTimeoutError:
                # Timeout is normal, just continue listening
                continue
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                time.sleep(1)  # Brief pause before retrying
    
    def _wait_for_command(self):
        """
        After wake word detected, wait for actual command
        """
        try:
            logger.info("Waiting for command...")
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            command = self._recognize_speech(audio)
            if command:
                logger.info(f"Command received: {command}")
                self._process_command(command)
        
        except sr.WaitTimeoutError:
            logger.warning("No command received after wake word")
        except Exception as e:
            logger.error(f"Error waiting for command: {e}")
    
    def _recognize_speech(self, audio) -> Optional[str]:
        """
        Convert audio to text using Google Speech Recognition
        """
        try:
            # Use Google's free speech recognition
            text = self.recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            logger.debug("Could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error recognizing speech: {e}")
            return None
    
    def _process_command(self, command: str):
        """
        Process recognized command
        """
        # Add to queue
        self.command_queue.put(command)
        
        # Call callback if provided
        if self.callback:
            try:
                self.callback(command)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def get_command(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Get next command from queue (blocking)
        """
        try:
            return self.command_queue.get(timeout=timeout)
        except queue.Empty:
            return None

# Example usage
if __name__ == "__main__":
    def command_callback(cmd):
        print(f"Command received: {cmd}")
    
    listener = VoiceListener(wake_word="hey assistant", callback=command_callback)
    listener.start()
    
    try:
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("Stopped")
