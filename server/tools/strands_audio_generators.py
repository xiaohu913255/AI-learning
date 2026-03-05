"""
Strands格式的音频生成工具
"""

__STRANDS_TOOL__ = False
__all__ = ['create_generate_audio_with_context']

import json
import os
from typing import Annotated
from pydantic import Field
from services.config_service import FILES_DIR
from services.db_service import db_service
from services.websocket_service import send_to_websocket
from tools.audio_generators import ComfyUIAudioGenerator


def create_generate_audio_with_context(
    session_id: str,
    canvas_id: str,
    audio_model: dict,
    user_id: str = None
):
    """
    创建带上下文的音频生成工具

    Args:
        session_id: 会话ID
        canvas_id: 画布ID
        audio_model: 音频模型配置 {"provider": "comfyui", "model": "t2a-model"}
        user_id: 用户ID
    """
    from strands import tool

    @tool
    async def generate_audio_with_context(
        prompt: Annotated[str, Field(description="Text to convert to speech/audio")],
        input_audio: Annotated[str, Field(description="Optional reference audio file ID (e.g., 'au_xxx.mp3') to clone voice style. Leave empty to use default voice.")] = "",
    ):
        """
        Generate audio from text using ComfyUI TTS workflow.

        Args:
            prompt: The text to convert to audio

        Returns:
            Success message with audio file information
        """
        try:
            print(f"🎵 generate_audio_with_context called")
            print(f"🔍 DEBUG: prompt={prompt[:100]}")
            print(f"🔍 DEBUG: audio_model={audio_model}")

            # 创建上下文
            ctx = {
                'session_id': session_id,
                'canvas_id': canvas_id,
                'user_id': user_id
            }

            # 获取 ComfyUI 配置
            from services.config_service import config_service
            comfyui_config = config_service.app_config.get('comfyui', {})
            comfyui_url = comfyui_config.get('url', '')

            # 生成音频
            generator = ComfyUIAudioGenerator()
            audio_id, duration, filename = await generator.generate(
                prompt=prompt,
                model=audio_model.get('model', 't2a-model'),
                input_audio=input_audio,
                ctx=ctx
            )

            print(f"✅ Audio generated: {filename}, duration: {duration}s")

            # 保存文件记录到数据库
            file_path = filename
            db_service.create_file(
                file_id=audio_id,
                file_path=file_path,
            )

            # 发送 WebSocket 通知
            await send_to_websocket(session_id, {
                'type': 'file_generated',
                'file_id': audio_id,
                'file_type': 'audio',
                'url': f'/api/file/{filename}'
            })

            # 创建音频消息并保存
            audio_message = {
                'role': 'assistant',
                'content': [
                    {
                        'type': 'audio_type',
                        'audio_url': {
                            'url': f'/api/file/{filename}'
                        }
                    }
                ]
            }
            db_service.create_message(session_id, 'assistant', json.dumps(audio_message))

            return f"Audio generated successfully! File ID: {audio_id}, Duration: {duration}s, Download: /api/file/{filename}"

        except Exception as e:
            import traceback
            error_msg = f"Failed to generate audio: {str(e)}"
            print(f"❌ {error_msg}")
            traceback.print_exc()

            await send_to_websocket(session_id, {
                'type': 'error',
                'error': error_msg
            })

            return f"Error: {error_msg}"

    return generate_audio_with_context
