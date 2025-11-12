"""
Kokoro TTS Server Client
Client library for interacting with the Kokoro TTS production server.
Supports synchronous and asynchronous operations, batch processing, and audio handling.
Features real-time text input processing with automatic audio playback.
"""

import base64
import json
import logging
import subprocess
import sys
import threading
from pathlib import Path
from queue import Queue
from typing import Callable, Dict, List, Optional, Tuple, Union

import httpx
import numpy as np

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("kokoro_tts_client")


class KokoroTTSClient:
    """
    Client for Kokoro TTS Server.
    
    Example:
        client = KokoroTTSClient("http://localhost:8000")
        response = client.synthesize(
            text="Hello, world!",
            voice="af_heart",
            lang_code="a"
        )
        audio = response.get_audio()
        audio.save("output.wav")
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 60.0,
        verify_ssl: bool = True
    ):
        """
        Initialize the Kokoro TTS client.
        
        Args:
            base_url: Base URL of the TTS server (default: http://localhost:8000)
            timeout: Request timeout in seconds (default: 60.0)
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client = httpx.Client(
            timeout=timeout,
            verify=verify_ssl
        )
        logger.info(f"Initialized KokoroTTSClient with base_url: {self.base_url}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def close(self):
        """Close the HTTP client"""
        self._client.close()
        logger.info("Closed KokoroTTSClient")
    
    def health_check(self) -> Dict[str, str]:
        """
        Check server health status.
        
        Returns:
            Dictionary with health status information
        
        Raises:
            httpx.HTTPError: If the request fails
        """
        try:
            response = self._client.get(f"{self.base_url}/healthz")
            response.raise_for_status()
            logger.info("Health check passed")
            return response.json()
        except httpx.HTTPError as exc:
            logger.error(f"Health check failed: {exc}")
            raise
    
    def server_info(self) -> Dict[str, object]:
        """
        Get server information and configuration.
        
        Returns:
            Dictionary with server info, defaults, and capabilities
        
        Raises:
            httpx.HTTPError: If the request fails
        """
        try:
            response = self._client.get(f"{self.base_url}/info")
            response.raise_for_status()
            logger.info("Retrieved server info")
            return response.json()
        except httpx.HTTPError as exc:
            logger.error(f"Failed to get server info: {exc}")
            raise
    
    def synthesize(
        self,
        text: str,
        voice: str = "af_heart",
        lang_code: str = "a",
        speed: float = 1.0
    ) -> "SynthesisResult":
        """
        Synthesize text to speech.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (default: "af_heart")
            lang_code: Language code (default: "a" for English)
            speed: Speech speed multiplier 0.5-2.0 (default: 1.0)
        
        Returns:
            SynthesisResult containing audio and metadata
        
        Raises:
            ValueError: If input validation fails
            httpx.HTTPError: If the request fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        logger.info(
            f"Synthesizing: text_len={len(text)}, voice={voice}, "
            f"lang_code={lang_code}, speed={speed}"
        )
        
        payload = {
            "text": text,
            "voice": voice,
            "lang_code": lang_code,
            "speed": speed
        }
        
        try:
            response = self._client.post(
                f"{self.base_url}/synthesize",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Synthesis successful: duration={data.get('audio_duration_seconds', 'N/A')}s")
            return SynthesisResult(data)
        except httpx.HTTPError as exc:
            logger.error(f"Synthesis failed: {exc}")
            raise
    
    def synthesize_batch(
        self,
        requests: List[Dict[str, Union[str, float]]]
    ) -> List["SynthesisResult"]:
        """
        Synthesize multiple texts in batch.
        
        Args:
            requests: List of synthesis request dictionaries with keys:
                     text, voice (optional), lang_code (optional), speed (optional)
        
        Returns:
            List of SynthesisResult objects
        
        Raises:
            ValueError: If input validation fails
            httpx.HTTPError: If the request fails
        """
        if not requests:
            raise ValueError("Requests list cannot be empty")
        
        if len(requests) > 10:
            raise ValueError("Maximum 10 requests per batch")
        
        logger.info(f"Batch synthesis: {len(requests)} items")
        
        # Validate and normalize requests
        normalized_requests = []
        for req in requests:
            if not isinstance(req, dict) or "text" not in req:
                raise ValueError("Each request must be a dict with 'text' key")
            if not req["text"] or not req["text"].strip():
                raise ValueError("Text in request cannot be empty")
            
            normalized_requests.append({
                "text": req["text"],
                "voice": req.get("voice", "af_heart"),
                "lang_code": req.get("lang_code", "a"),
                "speed": req.get("speed", 1.0)
            })
        
        try:
            response = self._client.post(
                f"{self.base_url}/synthesize-batch",
                json=normalized_requests
            )
            response.raise_for_status()
            data = response.json()
            results = [SynthesisResult(item) for item in data]
            logger.info(f"Batch synthesis completed: {len(results)} items")
            return results
        except httpx.HTTPError as exc:
            logger.error(f"Batch synthesis failed: {exc}")
            raise


class SynthesisResult:
    """
    Represents a synthesis result from the server.
    
    Attributes:
        audio_base64: Base64-encoded audio data
        audio_sample_rate: Sample rate of the audio
        audio_duration_seconds: Duration of the audio in seconds
        voice: Voice used for synthesis
        lang_code: Language code used
        speed: Speed multiplier used
        text_length: Length of the input text
    """
    
    def __init__(self, data: Dict[str, object]):
        """Initialize from server response"""
        self.audio_base64 = str(data.get("audio_base64", ""))
        self.audio_sample_rate = int(data.get("audio_sample_rate", 24000))
        self.audio_duration_seconds = float(data.get("audio_duration_seconds", 0.0))
        self.voice = str(data.get("voice", ""))
        self.lang_code = str(data.get("lang_code", ""))
        self.speed = float(data.get("speed", 1.0))
        self.text_length = int(data.get("text_length", 0))
    
    def get_audio(self) -> np.ndarray:
        """
        Decode and return audio as numpy array (float32).
        
        Returns:
            NumPy array with audio samples
        """
        try:
            audio_bytes = base64.b64decode(self.audio_base64)
            audio = np.frombuffer(audio_bytes, dtype=np.float32)
            logger.debug(f"Decoded audio: shape={audio.shape}, duration={self.audio_duration_seconds}s")
            return audio
        except Exception as exc:
            logger.error(f"Failed to decode audio: {exc}")
            raise
    
    def save_wav(self, filepath: Union[str, Path]) -> None:
        """
        Save audio to WAV file.
        
        Args:
            filepath: Path to save the WAV file
        
        Raises:
            ImportError: If soundfile is not installed
            Exception: If file writing fails
        """
        try:
            import soundfile as sf
        except ImportError:
            raise ImportError("soundfile is required. Install with: pip install soundfile")
        
        try:
            filepath = Path(filepath)
            audio = self.get_audio()
            sf.write(
                filepath,
                audio,
                self.audio_sample_rate,
                subtype='PCM_16'
            )
            logger.info(f"Saved audio to {filepath}")
        except Exception as exc:
            logger.error(f"Failed to save WAV file: {exc}")
            raise
    
    def save_raw(self, filepath: Union[str, Path]) -> None:
        """
        Save raw audio data (float32 binary).
        
        Args:
            filepath: Path to save the raw file
        """
        try:
            filepath = Path(filepath)
            audio = self.get_audio()
            audio.tofile(filepath)
            logger.info(f"Saved raw audio to {filepath}")
        except Exception as exc:
            logger.error(f"Failed to save raw audio: {exc}")
            raise
    
    def play(self, use_scipy: bool = True) -> bool:
        """
        Play the synthesized audio automatically.
        
        Args:
            use_scipy: Use scipy for audio playback if available
        
        Returns:
            True if playback succeeded, False otherwise
        """
        try:
            audio = self.get_audio()
            return AudioPlayer.play_audio(audio, self.audio_sample_rate, use_scipy=True)
        except Exception as exc:
            logger.error(f"Playback failed: {exc}")
            return False
    
    def to_dict(self) -> Dict[str, object]:
        """Convert result to dictionary (without audio data)"""
        return {
            "audio_sample_rate": self.audio_sample_rate,
            "audio_duration_seconds": self.audio_duration_seconds,
            "voice": self.voice,
            "lang_code": self.lang_code,
            "speed": self.speed,
            "text_length": self.text_length
        }
    
    def __repr__(self) -> str:
        """String representation"""
        return (
            f"SynthesisResult(voice={self.voice}, lang={self.lang_code}, "
            f"duration={self.audio_duration_seconds:.2f}s, speed={self.speed})"
        )


class AudioPlayer:
    """
    Cross-platform audio player for synthesized audio.
    Supports Windows (waveaudio), Linux (paplay/aplay), and macOS (afplay).
    """
    
    @staticmethod
    def get_player_command() -> Tuple[Optional[str], List[str]]:
        """
        Detect the appropriate audio player for the current platform.
        
        Returns:
            Tuple of (player_name, command_list)
        """
        import platform
        system = platform.system()
        
        if system == "Windows":
            return "Windows Media Player", []  # Use scipy/pygame on Windows
        elif system == "Darwin":  # macOS
            return "afplay", ["afplay"]
        elif system == "Linux":
            # Try paplay first (PulseAudio), then aplay (ALSA)
            try:
                subprocess.run(["paplay", "--version"], capture_output=True, check=True)
                return "paplay", ["paplay"]
            except (FileNotFoundError, subprocess.CalledProcessError):
                try:
                    subprocess.run(["aplay", "--version"], capture_output=True, check=True)
                    return "aplay", ["aplay"]
                except FileNotFoundError:
                    return None, []
        
        return None, []
    
    @staticmethod
    def play_audio(
        audio: np.ndarray,
        sample_rate: int = 24000,
        use_scipy: bool = True
    ) -> bool:
        """
        Play audio using the best available method.
        
        Args:
            audio: Audio data as numpy array (float32)
            sample_rate: Sample rate in Hz
            use_scipy: Try scipy/pygame methods first
        
        Returns:
            True if playback succeeded, False otherwise
        """
        import platform
        system = platform.system()
        
        # Normalize audio
        audio_max = np.max(np.abs(audio))
        if audio_max > 1.0:
            audio = audio / (audio_max * 1.05)
        
        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)
        
        # Try scipy first (cross-platform, better for Windows)
        if use_scipy:
            try:
                from scipy.io import wavfile as scipy_wavfile
                import tempfile
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    temp_path = tmp.name
                
                try:
                    scipy_wavfile.write(temp_path, sample_rate, audio_int16)
                    
                    # Try platform-specific command first
                    if system == "Windows":
                        # On Windows, try PowerShell to play audio
                        try:
                            ps_cmd = f'[System.Media.SoundPlayer]::new("{temp_path}").PlaySync()'
                            subprocess.run(
                                ["powershell", "-Command", ps_cmd],
                                check=True,
                                capture_output=True,
                                timeout=300
                            )
                            logger.info("Playback succeeded using Windows PowerShell")
                            Path(temp_path).unlink()
                            return True
                        except Exception as ps_exc:
                            logger.debug(f"PowerShell playback failed: {ps_exc}")
                    
                    elif system == "Darwin":  # macOS
                        try:
                            subprocess.run(
                                ["afplay", temp_path],
                                check=True,
                                capture_output=True,
                                timeout=300
                            )
                            logger.info("Playback succeeded using afplay")
                            Path(temp_path).unlink()
                            return True
                        except Exception as afplay_exc:
                            logger.debug(f"afplay failed: {afplay_exc}")
                    
                    elif system == "Linux":
                        # Try paplay first, then aplay
                        for player_cmd in [["paplay"], ["aplay"]]:
                            try:
                                subprocess.run(
                                    player_cmd + [temp_path],
                                    check=True,
                                    capture_output=True,
                                    timeout=300
                                )
                                logger.info(f"Playback succeeded using {player_cmd[0]}")
                                Path(temp_path).unlink()
                                return True
                            except (FileNotFoundError, subprocess.CalledProcessError):
                                continue
                    
                    # If command-based playback failed, clean up and continue to pygame
                    try:
                        Path(temp_path).unlink()
                    except:
                        pass
                
                except Exception as exc:
                    logger.debug(f"scipy playback with command failed: {exc}")
                    try:
                        Path(temp_path).unlink()
                    except:
                        pass
            
            except ImportError:
                logger.debug("scipy not available, trying pygame")
        
        # Fallback: Try using pygame (works on Windows if scipy fails)
        try:
            import pygame
            import time
            
            # Initialize pygame mixer
            try:
                pygame.mixer.quit()  # Stop any previous mixer
            except:
                pass
            
            pygame.mixer.init(frequency=sample_rate, size=-16, channels=1, buffer=512)
            
            # Create sound from array
            sound = pygame.sndarray.make_sound(audio_int16)
            sound.play()
            
            # Wait for playback to finish
            duration = len(audio_int16) / sample_rate
            time.sleep(duration + 0.1)
            
            pygame.mixer.quit()
            logger.info("Playback succeeded using pygame")
            return True
        
        except ImportError:
            logger.error("pygame not available")
        except Exception as exc:
            logger.error(f"pygame playback failed: {exc}")
        
        return False


class AsyncKokoroTTSClient:
    """
    Asynchronous client for Kokoro TTS Server.
    
    Example:
        async with AsyncKokoroTTSClient("http://localhost:8000") as client:
            response = await client.synthesize("Hello, world!")
            audio = response.get_audio()
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 60.0,
        verify_ssl: bool = True
    ):
        """
        Initialize the async Kokoro TTS client.
        
        Args:
            base_url: Base URL of the TTS server
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(f"Initialized AsyncKokoroTTSClient with base_url: {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            verify=self.verify_ssl
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def close(self):
        """Close the async HTTP client"""
        if self._client:
            await self._client.aclose()
            logger.info("Closed AsyncKokoroTTSClient")
    
    async def health_check(self) -> Dict[str, str]:
        """Check server health status asynchronously"""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with statement.")
        try:
            response = await self._client.get(f"{self.base_url}/healthz")
            response.raise_for_status()
            logger.info("Async health check passed")
            return response.json()
        except httpx.HTTPError as exc:
            logger.error(f"Async health check failed: {exc}")
            raise
    
    async def synthesize(
        self,
        text: str,
        voice: str = "af_heart",
        lang_code: str = "a",
        speed: float = 1.0
    ) -> "SynthesisResult":
        """Synthesize text to speech asynchronously"""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with statement.")
        
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        logger.info(f"Async synthesis: text_len={len(text)}, voice={voice}")
        
        payload = {
            "text": text,
            "voice": voice,
            "lang_code": lang_code,
            "speed": speed
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/synthesize",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Async synthesis successful: duration={data.get('audio_duration_seconds')}s")
            return SynthesisResult(data)
        except httpx.HTTPError as exc:
            logger.error(f"Async synthesis failed: {exc}")
            raise
    
    async def synthesize_batch(
        self,
        requests: List[Dict[str, Union[str, float]]]
    ) -> List["SynthesisResult"]:
        """Synthesize multiple texts in batch asynchronously"""
        if not self._client:
            raise RuntimeError("Client not initialized. Use async with statement.")
        
        if not requests or len(requests) > 10:
            raise ValueError("Requests must be 1-10 items")
        
        logger.info(f"Async batch synthesis: {len(requests)} items")
        
        try:
            response = await self._client.post(
                f"{self.base_url}/synthesize-batch",
                json=requests
            )
            response.raise_for_status()
            data = response.json()
            results = [SynthesisResult(item) for item in data]
            logger.info(f"Async batch synthesis completed: {len(results)} items")
            return results
        except httpx.HTTPError as exc:
            logger.error(f"Async batch synthesis failed: {exc}")
            raise


# Convenience functions for simple usage
def synthesize(
    text: str,
    base_url: str = "http://localhost:8000",
    voice: str = "af_heart",
    lang_code: str = "a",
    speed: float = 1.0
) -> SynthesisResult:
    """
    Simple function to synthesize text without managing client lifecycle.
    
    Args:
        text: Text to synthesize
        base_url: Server base URL
        voice: Voice to use
        lang_code: Language code
        speed: Speed multiplier
    
    Returns:
        SynthesisResult
    """
    with KokoroTTSClient(base_url) as client:
        return client.synthesize(text, voice, lang_code, speed)


def health_check(base_url: str = "http://localhost:8000") -> Dict[str, str]:
    """Check server health"""
    with KokoroTTSClient(base_url) as client:
        return client.health_check()


class InteractiveRealtimeClient:
    """
    Real-time interactive TTS client with automatic audio playback.
    Continuously listens for user input and synthesizes text to speech.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        voice: str = "af_heart",
        lang_code: str = "a",
        speed: float = 1.0,
        auto_play: bool = True,
        save_history: bool = False,
        history_dir: Optional[Path] = None
    ):
        """
        Initialize interactive client.
        
        Args:
            base_url: Server URL
            voice: Default voice
            lang_code: Default language code
            speed: Default speech speed
            auto_play: Automatically play audio after synthesis
            save_history: Save synthesized audio to files
            history_dir: Directory for saving audio files
        """
        self.client = KokoroTTSClient(base_url)
        self.voice = voice
        self.lang_code = lang_code
        self.speed = speed
        self.auto_play = auto_play
        self.save_history = save_history
        
        if save_history:
            self.history_dir = Path(history_dir or "tts_history")
            self.history_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"History will be saved to {self.history_dir}")
        else:
            self.history_dir = None
        
        self.synthesis_count = 0
        logger.info("Initialized InteractiveRealtimeClient")
    
    def _save_audio_history(self, text: str, result: SynthesisResult) -> None:
        """Save synthesized audio to history directory"""
        if not self.save_history or not self.history_dir:
            return
        
        try:
            # Create filename based on synthesis count
            timestamp = self.synthesis_count
            safe_text = "".join(
                c if c.isalnum() else "_" for c in text[:30]
            ).lower()
            filename = f"{timestamp:04d}_{safe_text}.wav"
            filepath = self.history_dir / filename
            
            result.save_wav(filepath)
            logger.info(f"Saved to history: {filename}")
        except Exception as exc:
            logger.error(f"Failed to save to history: {exc}")
    
    def _process_input(self, text: str, voice: Optional[str] = None) -> bool:
        """
        Process a single text input: synthesize and play.
        
        Args:
            text: Text to synthesize
            voice: Optional voice override
        
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logger.warning("Empty input, skipping")
            return False
        
        try:
            self.synthesis_count += 1
            effective_voice = voice or self.voice
            
            logger.info(
                f"\n[{self.synthesis_count}] Synthesizing: \"{text[:50]}...\""
                if len(text) > 50 else f"\n[{self.synthesis_count}] Synthesizing: \"{text}\""
            )
            
            # Synthesize
            result = self.client.synthesize(
                text=text,
                voice=effective_voice,
                lang_code=self.lang_code,
                speed=self.speed
            )
            
            logger.info(f"✓ Synthesis complete ({result.audio_duration_seconds:.2f}s)")
            
            # Save to history if enabled
            if self.save_history:
                self._save_audio_history(text, result)
            
            # Auto-play if enabled
            if self.auto_play:
                logger.info("▶ Playing audio...")
                success = result.play()
                if success:
                    logger.info("✓ Playback complete")
                else:
                    logger.warning("✗ Playback failed (scipy/pygame required)")
            
            return True
        
        except ValueError as exc:
            logger.error(f"✗ Input error: {exc}")
            return False
        except Exception as exc:
            logger.error(f"✗ Synthesis error: {exc}")
            return False
    
    def run_interactive(self) -> None:
        """Run interactive real-time mode with command interface"""
        print("\n" + "="*70)
        print("  Kokoro TTS - Real-Time Interactive Client")
        print("="*70)
        print("\nCommands:")
        print("  [text]        - Synthesize text (default voice)")
        print("  voice:[name]  - Set voice (e.g., 'voice:af' or 'voice:af_heart')")
        print("  speed:[value] - Set speed (e.g., 'speed:0.8' or 'speed:1.5')")
        print("  lang:[code]   - Set language (e.g., 'lang:a' for English)")
        print("  play:[toggle] - Toggle auto-play (on/off)")
        print("  info          - Show server info")
        print("  help          - Show this help")
        print("  quit/exit     - Exit the program")
        print("="*70 + "\n")
        
        try:
            # Verify server connection
            logger.info("Checking server connection...")
            info = self.client.server_info()
            logger.info(f"✓ Connected to server v{info.get('version')}")
            print()
            
            # Main input loop
            while True:
                try:
                    user_input = input("TTS> ").strip()
                    
                    if not user_input:
                        continue
                    
                    # Process commands
                    if user_input.lower() in ["quit", "exit"]:
                        print("\nGoodbye!")
                        break
                    
                    elif user_input.lower() == "help":
                        print("\nCommands:")
                        print("  [text]        - Synthesize text")
                        print("  voice:[name]  - Change voice")
                        print("  speed:[value] - Change speed (0.5-2.0)")
                        print("  lang:[code]   - Change language")
                        print("  play:[on/off] - Toggle auto-play")
                        print("  info          - Server info")
                        print("  help          - This help")
                        print("  quit/exit     - Exit")
                        print()
                        continue
                    
                    elif user_input.lower() == "info":
                        info = self.client.server_info()
                        print("\nServer Information:")
                        for key, value in info.items():
                            print(f"  {key}: {value}")
                        print()
                        continue
                    
                    elif user_input.lower().startswith("voice:"):
                        new_voice = user_input[6:].strip()
                        if new_voice:
                            self.voice = new_voice
                            logger.info(f"✓ Voice changed to: {self.voice}")
                        continue
                    
                    elif user_input.lower().startswith("speed:"):
                        try:
                            new_speed = float(user_input[6:].strip())
                            if 0.5 <= new_speed <= 2.0:
                                self.speed = new_speed
                                logger.info(f"✓ Speed changed to: {self.speed}")
                            else:
                                logger.warning("Speed must be between 0.5 and 2.0")
                        except ValueError:
                            logger.error("Invalid speed value")
                        continue
                    
                    elif user_input.lower().startswith("lang:"):
                        new_lang = user_input[5:].strip()
                        if new_lang:
                            self.lang_code = new_lang
                            logger.info(f"✓ Language changed to: {self.lang_code}")
                        continue
                    
                    elif user_input.lower().startswith("play:"):
                        toggle = user_input[5:].strip().lower()
                        if toggle in ["on", "true", "1", "yes"]:
                            self.auto_play = True
                            logger.info("✓ Auto-play enabled")
                        elif toggle in ["off", "false", "0", "no"]:
                            self.auto_play = False
                            logger.info("✓ Auto-play disabled")
                        continue
                    
                    # Treat as text to synthesize
                    self._process_input(user_input)
                
                except KeyboardInterrupt:
                    print("\n\nInterrupted by user")
                    break
                except Exception as exc:
                    logger.error(f"Unexpected error: {exc}")
        
        finally:
            self.client.close()
            logger.info("Client closed")
    
    def run_batch_from_file(self, filepath: Union[str, Path]) -> None:
        """
        Process text from a file, one line per synthesis.
        
        Args:
            filepath: Path to text file
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            logger.info(f"Processing {len(lines)} lines from {filepath}")
            
            for i, line in enumerate(lines, 1):
                text = line.strip()
                if text:  # Skip empty lines
                    logger.info(f"\n[{i}/{len(lines)}]")
                    self._process_input(text)
            
            logger.info("\n✓ Batch processing complete")
        
        except Exception as exc:
            logger.error(f"Failed to process file: {exc}")
        
        finally:
            self.client.close()


def interactive_mode(
    base_url: str = "http://localhost:8000",
    voice: str = "af_heart",
    lang_code: str = "a",
    speed: float = 1.0,
    auto_play: bool = True,
    save_history: bool = False
) -> None:
    """
    Launch interactive real-time TTS client.
    
    Args:
        base_url: Server URL
        voice: Default voice
        lang_code: Default language code
        speed: Default speech speed
        auto_play: Auto-play synthesized audio
        save_history: Save audio files to disk
    """
    client = InteractiveRealtimeClient(
        base_url=base_url,
        voice=voice,
        lang_code=lang_code,
        speed=speed,
        auto_play=auto_play,
        save_history=save_history
    )
    client.run_interactive()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Kokoro TTS Client - Real-time interactive or batch mode"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Launch interactive real-time mode"
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        metavar="FILE",
        help="Process text file in batch mode (one line per synthesis)"
    )
    parser.add_argument(
        "--text", "-t",
        type=str,
        metavar="TEXT",
        help="Synthesize single text"
    )
    parser.add_argument(
        "--url", "-u",
        type=str,
        default="http://localhost:8000",
        help="Server URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--voice", "-v",
        type=str,
        default="af_heart",
        help="Voice name (default: af_heart)"
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="a",
        help="Language code (default: a for English)"
    )
    parser.add_argument(
        "--speed", "-s",
        type=float,
        default=1.0,
        help="Speech speed (default: 1.0, range: 0.5-2.0)"
    )
    parser.add_argument(
        "--play", "-p",
        action="store_true",
        help="Auto-play audio"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save audio files to disk"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        metavar="FILE",
        help="Output file path (for single text synthesis)"
    )
    
    args = parser.parse_args()
    
    # Default to interactive mode if no other mode specified
    if not args.text and not args.batch and not args.interactive:
        args.interactive = True
    
    try:
        if args.interactive:
            interactive_mode(
                base_url=args.url,
                voice=args.voice,
                lang_code=args.lang,
                speed=args.speed,
                auto_play=args.play or True,
                save_history=args.save
            )
        
        elif args.text:
            logger.info(f"Synthesizing: {args.text}")
            result = synthesize(
                text=args.text,
                base_url=args.url,
                voice=args.voice,
                lang_code=args.lang,
                speed=args.speed
            )
            logger.info(f"✓ Synthesis complete: {result}")
            
            if args.play:
                result.play()
            
            if args.output:
                result.save_wav(args.output)
                logger.info(f"✓ Saved to {args.output}")
        
        elif args.batch:
            client = InteractiveRealtimeClient(
                base_url=args.url,
                voice=args.voice,
                lang_code=args.lang,
                speed=args.speed,
                auto_play=args.play,
                save_history=args.save
            )
            client.run_batch_from_file(args.batch)
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Fatal error: {exc}", exc_info=True)
        sys.exit(1)
