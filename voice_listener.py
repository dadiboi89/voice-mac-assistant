"""
Voice Listener - Handles voice input capture and speech-to-text
Uses Whisper for free, offline speech recognition
"""
import whisper
import pyaudio
import numpy as np
from loguru import logger
import threading
import queue
from typing import Optional, Callable
import time

class VoiceListener:
    """
    Continuously listens for voice commands using Whisper
    - Detects wake word ("Hey Assistant" or similar)
    - Captures voice input
    - Converts to text using Whisper (free, offline)
    - Passes text to callback function
    """
    
    def __init__(self, wake_word: str = "hey assistant", callback: Optional[Callable] = None, model_size: str = "base"):
        self.wake_word = wake_word.lower()
        self.callback = callback
        self.is_listening = False
        self.command_queue = queue.Queue()
        self.listen_thread = None
        
        # Audio settings
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.RECORD_SECONDS = 5
        
        # Initialize Whisper model
        logger.info(f"Loading Whisper {model_size} model...")
        self.model = whisper.load_model(model_size)
        logger.info("Whisper model loaded")
        
        self.audio = pyaudio.PyAudio()
        
    def start(self):
        """Start listening for voice commands in background thread"""
        if self.is_listening:
            logger.warning("Already listening")
            return
        
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        logger.info(f"Voice listener started. Say '{self.wake_word}' to activate")
    
    def stop(self):
        """Stop listening"""
        self.is_listening = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        self.audio.terminate()
        logger.info("Voice listener stopped")
    
    def _listen_loop(self):
        """Main listening loop - runs in background thread"""
        while self.is_listening:
            try:
                audio_data = self._record_audio()
                text = self._recognize_speech_whisper(audio_data)
                
                if text:
                    logger.info(f"Heard: {text}")
                    
                    if self.wake_word in text.lower():
                        logger.info("Wake word detected!")
                        command = text.lower().replace(self.wake_word, "").strip()
                        
                        if command:
                            logger.info(f"Command: {command}")
                            self._process_command(command)
                        else:
                            self._wait_for_command()
                
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                time.sleep(1)
    
    def _record_audio(self) -> np.ndarray:
        """Record audio from microphone"""
        stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )
        
        logger.debug("Listening...")
        frames = []
        
        for _ in range(0, int(self.RATE / self.CHUNK * self.RECORD_SECONDS)):
            data = stream.read(self.CHUNK)
            frames.append(data)
        
        stream.stop_stream()
        stream.close()
        
        audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
        audio_data = audio_data.astype(np.float32) / 32768.0
        
        return audio_data
    
    def _recognize_speech_whisper(self, audio_data: np.ndarray) -> Optional[str]:
        """Convert audio to text using Whisper"""
        try:
            result = self.model.transcribe(audio_data, fp16=False)
            text = result["text"].strip()
            return text if text else None
        except Exception as e:
            logger.error(f"Error recognizing speech with Whisper: {e}")
            return None
    
    def _wait_for_command(self):
        """After wake word detected, wait for actual command"""
        try:
            logger.info("Waiting for command...")
            audio_data = self._record_audio()
            command = self._recognize_speech_whisper(audio_data)
            
            if command:
                logger.info(f"Command received: {command}")
                self._process_command(command)
        except Exception as e:
            logger.error(f"Error waiting for command: {e}")
    
    def _process_command(self, command: str):
        """Process recognized command"""
        self.command_queue.put(command)
        
        if self.callback:
            try:
                self.callback(command)
            except Exception as e:
                logger.error(f"Error in callback: {e}")
    
    def get_command(self, timeout: Optional[float] = None) -> Optional[str]:
        """Get next command from queue (blocking)"""
        try:
            return self.command_queue.get(timeout=timeout)
        except queue.Empty:
            return None

if __name__ == "__main__":
    def command_callback(cmd):
        print(f"Command received: {cmd}")
    
    listener = VoiceListener(wake_word="hey assistant", callback=command_callback, model_size="base")
    listener.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        print("Stopped")
