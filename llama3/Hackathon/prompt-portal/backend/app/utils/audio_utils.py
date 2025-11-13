"""
Audio utilities for handling raw PCM audio data
Converts raw audio bytes to WAV format for STT/TTS processing
"""

import io
import struct
import logging

logger = logging.getLogger(__name__)


def add_wav_header(
    audio_data: bytes,
    sample_rate: int = 16000,
    num_channels: int = 1,
    sample_width: int = 2
) -> bytes:
    """
    Add WAV header to raw PCM audio data.
    
    Args:
        audio_data: Raw PCM audio bytes
        sample_rate: Sample rate in Hz (default: 16000)
        num_channels: Number of channels (default: 1 for mono)
        sample_width: Bytes per sample (default: 2 for 16-bit)
    
    Returns:
        Complete WAV file data with header
    """
    if not audio_data:
        raise ValueError("Audio data is empty")
    
    try:
        # WAV format specification
        byte_rate = sample_rate * num_channels * sample_width
        block_align = num_channels * sample_width
        
        # Audio subchunk
        audio_subchunk_size = len(audio_data)
        subchunk2_id = b'data'
        subchunk2_size = audio_subchunk_size
        
        # Format subchunk
        subchunk1_id = b'fmt '
        subchunk1_size = 16
        audio_format = 1  # PCM
        
        # Build WAV header
        wav_header = io.BytesIO()
        
        # RIFF header
        wav_header.write(b'RIFF')
        wav_header.write(struct.pack('<I', 36 + audio_subchunk_size))
        wav_header.write(b'WAVE')
        
        # Format subchunk
        wav_header.write(subchunk1_id)
        wav_header.write(struct.pack('<I', subchunk1_size))
        wav_header.write(struct.pack('<H', audio_format))
        wav_header.write(struct.pack('<H', num_channels))
        wav_header.write(struct.pack('<I', sample_rate))
        wav_header.write(struct.pack('<I', byte_rate))
        wav_header.write(struct.pack('<H', block_align))
        wav_header.write(struct.pack('<H', sample_width * 8))
        
        # Data subchunk
        wav_header.write(subchunk2_id)
        wav_header.write(struct.pack('<I', subchunk2_size))
        wav_header.write(audio_data)
        
        result = wav_header.getvalue()
        logger.debug(
            f"WAV header added: {len(audio_data)} bytes PCM → {len(result)} bytes WAV "
            f"(sample_rate={sample_rate}, channels={num_channels}, sample_width={sample_width})"
        )
        return result
        
    except Exception as exc:
        logger.error(f"Failed to add WAV header: {exc}", exc_info=True)
        raise


def detect_audio_format(audio_data: bytes) -> dict:
    """
    Detect if audio data is already in WAV format or raw PCM.
    
    Args:
        audio_data: Audio bytes to check
    
    Returns:
        Dict with format info: {"is_wav": bool, "format": "wav" or "pcm"}
    """
    if len(audio_data) < 4:
        return {"is_wav": False, "format": "pcm"}
    
    # Check for RIFF/WAV signature
    if audio_data[:4] == b'RIFF' and len(audio_data) >= 12 and audio_data[8:12] == b'WAVE':
        return {"is_wav": True, "format": "wav"}
    
    return {"is_wav": False, "format": "pcm"}


def ensure_wav_format(audio_data: bytes, sample_rate: int = 16000) -> bytes:
    """
    Ensure audio data is in WAV format.
    If already WAV, return as-is. If raw PCM, add header.
    
    Args:
        audio_data: Audio bytes (may be WAV or raw PCM)
        sample_rate: Sample rate to use if adding header
    
    Returns:
        Audio data guaranteed to be in WAV format
    """
    format_info = detect_audio_format(audio_data)
    
    if format_info["is_wav"]:
        logger.debug("Audio is already in WAV format, using as-is")
        return audio_data
    else:
        logger.debug("Audio is raw PCM, adding WAV header")
        return add_wav_header(audio_data, sample_rate=sample_rate)
