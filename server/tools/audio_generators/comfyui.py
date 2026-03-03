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

        return await self._run_t2a_workflow(prompt, host, port, ctx)

    async def _run_t2a_workflow(self, user_prompt: str, host: str, port: str, ctx: dict) -> tuple[str, int, str]:
        """Run text-to-audio workflow"""
        print(f"🔍 DEBUG: _run_t2a_workflow called")
        workflow = copy.deepcopy(self.t2a_workflow)

        # 修改工作流中的文本节点（根据你的实际工作流调整节点 ID）
        # 假设节点 1 是文本输入节点
        if '11' in workflow:
            workflow['11']['inputs']['multi_line_prompt'] = user_prompt
        print(f"🔧 Workflow params (t2a): text_preview={user_prompt[:80]!r}")

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
