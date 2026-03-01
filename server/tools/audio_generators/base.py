from abc import ABC, abstractmethod
from typing import Optional, Tuple
import base64
import aiofiles
import os
import subprocess
import json
try:
    from nanoid import generate
except ImportError:
    import random
    import string
    def generate(size=8):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=size))
from utils.http_client import HttpClient


class AudioGenerator(ABC):
    """Abstract base class for audio generators"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> Tuple[str, int, str]:
        """
        Generate audio and return metadata

        Args:
            prompt: Text prompt for audio generation
            model: Model name/identifier
            **kwargs: Additional provider-specific parameters

        Returns:
            Tuple of (file_id, duration_seconds, filename)
        """
        pass


async def get_audio_info_and_save(url, file_path_without_extension, is_b64=False):
    """Shared utility function to download/decode and save audio"""
    if is_b64:
        audio_content = base64.b64decode(url)
    else:
        # Fetch the audio asynchronously
        async with HttpClient.create() as client:
            response = await client.get(url)
            audio_content = response.content

    # Save to temporary file first
    temp_path = f"{file_path_without_extension}.mp3"
    async with aiofiles.open(temp_path, 'wb') as out_file:
        await out_file.write(audio_content)

    print(f'🎵 Audio saved to {temp_path}')

    # Get audio metadata using ffprobe
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', temp_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)

        # Extract audio stream information
        audio_stream = None
        for stream in metadata.get('streams', []):
            if stream.get('codec_type') == 'audio':
                audio_stream = stream
                break

        if audio_stream:
            duration = float(metadata.get('format', {}).get('duration', 0))
            if duration == 0 and audio_stream.get('duration'):
                duration = float(audio_stream.get('duration', 0))
        else:
            duration = 0

    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"⚠️ Warning: Could not get audio metadata: {e}")
        duration = 0

    extension = 'mp3'
    return 'audio/mpeg', duration, extension


def generate_audio_id():
    """Generate unique audio ID"""
    return 'au_' + generate(size=10)
