from typing import Optional, Dict, Any
import os
import json
import sys
import copy
import random
import traceback
try:
    from .base import AudioGenerator, get_audio_info_and_save, generate_audio_id
except ImportError:
    from tools.audio_generators.base import AudioGenerator, get_audio_info_and_save, generate_audio_id
from services.config_service import config_service, FILES_DIR
from routers.comfyui_execution import execute


def get_asset_path(filename):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, 'asset', filename)


class ComfyUIAudioGenerator(AudioGenerator):
    """ComfyUI audio generator implementation"""

    def __init__(self):
        t2a_workflow_path = get_asset_path('t2a_workflow.json')
        self.t2a_workflow = None

        try:
            print(f"🔍 DEBUG: Loading ComfyUI audio workflow...")
            self.t2a_workflow = json.load(open(t2a_workflow_path, 'r'))
            print("✅ Loaded t2a_workflow")
        except FileNotFoundError:
            print("⚠️ t2a_workflow.json not found")
            self.t2a_workflow = None
        except Exception as e:
            print(f"❌ Error loading audio workflow: {e}")
            traceback.print_exc()

    async def generate(
        self,
        prompt: str,
        model: str,
        input_audio: Optional[str] = None,
        **kwargs
    ) -> tuple[str, int, str]:
        ctx = kwargs.get('ctx', {})
        print(f"🎵 ComfyUI generating audio: {model}")

        api_url = config_service.app_config.get('comfyui', {}).get('url', '')
        print(f"🔍 DEBUG: Using server-config ComfyUI URL: {api_url}")

        if not api_url:
            raise Exception("ComfyUI URL not configured")

        api_url = api_url.replace('http://', '').replace('https://', '')
        host = api_url.split(':')[0]
        port = api_url.split(':')[1]

        if not self.t2a_workflow:
            raise Exception('T2A workflow json not found')

        return await self._run_t2a_workflow(prompt,input_audio, host, port, ctx)

    async def _run_t2a_workflow(self, user_prompt: str, input_audio: Optional[str], host: str, port: str, ctx: dict) -> tuple[str, int, str]:
        """Run text-to-audio workflow with optional reference audio"""
        print(f"🔍 DEBUG: _run_t2a_workflow called")
        print(f"🔍 DEBUG: input_audio={input_audio}")

        workflow = copy.deepcopy(self.t2a_workflow)

        if '11' in workflow:
            workflow['11']['inputs']['multi_line_prompt'] = user_prompt
        print(f"🔧 Workflow params (t2a): text_preview={user_prompt[:80]!r}")

        # 如果有参考音频，上传到 ComfyUI
        if input_audio:
            import httpx
            from services.db_service import db_service

            audio_filename = input_audio
            if '.' not in input_audio:
                try:
                    file_record = db_service.get_file(input_audio)
                    if file_record and 'file_path' in file_record:
                        audio_filename = file_record['file_path']
                except:
                    pass

                if '.' not in audio_filename:
                    for ext in ['mp3', 'wav', 'MP3', 'WAV', 'm4a', 'ogg']:
                        test_path = os.path.join(FILES_DIR, f'{input_audio}.{ext}')
                        if os.path.exists(test_path):
                            audio_filename = f'{input_audio}.{ext}'
                            break

            audio_file_path = os.path.join(FILES_DIR, audio_filename)
            if os.path.exists(audio_file_path):
                print(f"📤 Uploading audio to ComfyUI: {audio_file_path}")
                async with httpx.AsyncClient(timeout=60.0) as client:
                    with open(audio_file_path, 'rb') as f:
                        files = {'image': (audio_filename, f, 'audio/mpeg')}
                        response = await client.post(f'http://{host}:{port}/upload/image', files=files)
                        if response.status_code == 200:
                            uploaded_filename = response.json().get('name', audio_filename)
                            print(f"✅ Audio uploaded: {uploaded_filename}")
                            # TODO: 配置工作流节点，例如：
                            if '63' in workflow:
                                workflow['63']['inputs']['audio'] = uploaded_filename

        execution = await execute(workflow, host, port, ctx=ctx)

        if not execution.outputs:
            raise Exception('No outputs from T2A workflow')

        url = execution.outputs[0]

        audio_id = generate_audio_id()
        mime_type, duration, extension = await get_audio_info_and_save(
            url, os.path.join(FILES_DIR, f'{audio_id}')
        )
        filename = f'{audio_id}.{extension}'
        return audio_id, int(duration), filename
