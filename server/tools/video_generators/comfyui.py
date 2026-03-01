from typing import Optional, Dict, Any
import os
import json
import sys
import copy
import random
import traceback
try:
    from .base import VideoGenerator, get_video_info_and_save, generate_video_id
except ImportError:
    # 使用绝对导入作为备用
    from tools.video_generators.base import VideoGenerator, get_video_info_and_save, generate_video_id
from services.config_service import config_service, FILES_DIR
from routers.comfyui_execution import execute


def get_asset_path(filename):
    # To get the correct path for pyinstaller bundled application
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, the path is relative to the executable
        base_path = sys._MEIPASS
    else:
        # If the application is run in a normal Python environment
        base_path = os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))))

    return os.path.join(base_path, 'asset', filename)


class ComfyUIVideoGenerator(VideoGenerator):
    """ComfyUI video generator implementation"""

    def __init__(self):
        # Load video workflows
        wan_t2v_workflow_path = get_asset_path('wanv_t2v.json')
        wan_i2v_workflow_path = get_asset_path('wan_i2v.json')
        db_workflow_path = get_asset_path('db_workflow.json')  # 新增
        wan_s2v_workflow_path = get_asset_path('wan_s2v.json')  # 新增
    

        self.wan_t2v_workflow = None
        self.wan_i2v_workflow = None
        self.add_audio_workflow = None
        self.wan_s2v_workflow = None  # 新增
        try:
            self.wan_t2v_workflow = json.load(open(wan_t2v_workflow_path, 'r'))
            self.wan_i2v_workflow = json.load(open(wan_i2v_workflow_path, 'r'))
            self.add_audio_workflow = json.load(open(db_workflow_path, 'r'))  # 新增
            self.wan_s2v_workflow = json.load(open(wan_s2v_workflow_path, 'r'))  # 新增

        except Exception as e:
            print(f"❌ Error loading video workflows: {e}")
            traceback.print_exc()

    async def generate(
        self,
        prompt: str,
        model: str,
        input_image: Optional[str] = None,
        input_video: Optional[str] = None,
        input_audio: Optional[str] = None,
        duration: int = 5,
        fps: int = 16,
        **kwargs
    ) -> tuple[str, int, int, int, str]:
        # Get context from kwargs
        ctx = kwargs.get('ctx', {})
        print(f"🎬 ComfyUI generating video: {model}")

        api_url = config_service.app_config.get('comfyui', {}).get('url', '')

        if not api_url:
            raise Exception("ComfyUI URL not configured")

        api_url = api_url.replace('http://', '').replace('https://', '')
        host = api_url.split(':')[0]
        port = api_url.split(':')[1]
        print(f"🔍*********** DEBUG: Original model value = '{model}'")
        print(f"🔍 DEBUG: model.lower() = '{model.lower()}'")

        # Determine workflow based on model and input
        if 's2v' in model.lower() or 'wan-s2v' in model.lower():
            # S2V (Speech-to-Video) workflow - 图片说话
            if not self.wan_s2v_workflow:
                raise Exception('S2V workflow json not found')
            if not input_image or not input_audio:
                raise Exception('S2V requires both input_image and input_audio')
            return await self._run_wan_s2v_workflow(prompt, input_image, input_audio, host, port, ctx)
        elif 'i2v' in model.lower() or input_image:
            # Image-to-video workflow
            if not self.wan_i2v_workflow:
                raise Exception('WAN I2V workflow json not found')
            return await self._run_wan_i2v_workflow(prompt, input_image, host, port, ctx)
        elif 'db-model' in model.lower():
            if not self.add_audio_workflow:
                raise Exception('Your new workflow json not found')
            return await self._run_add_audio_workflow(prompt, input_video or '', '', host, port, ctx)
        
        else:
            # Text-to-video workflow
            if not self.wan_t2v_workflow:
                raise Exception('WAN T2V workflow json not found')
            return await self._run_wan_t2v_workflow(prompt, host, port, ctx)
    
    async def _run_wan_s2v_workflow(
        self,
        user_prompt: str,
        input_image: str,
        input_audio: str,
        host: str,
        port: str,
        ctx: dict
    ) -> tuple[str, int, int, int, str]:
        """
        图片说话：根据音频和参考图生成口型同步的视频
        """
        workflow = copy.deepcopy(self.wan_s2v_workflow)

        # 配置正向提示词（节点6）
        workflow['6']['inputs']['text'] = user_prompt

        # 配置参考图片（节点52）
        workflow['52']['inputs']['image'] = input_image

        # 配置输入音频（节点58）
        workflow['58']['inputs']['audio'] = input_audio

        # 配置随机种子
        import random
        workflow['3']['inputs']['seed'] = random.randint(0, 99999999998)
        workflow['79:77']['inputs']['seed'] = random.randint(0, 99999999998)
        workflow['85:77']['inputs']['seed'] = random.randint(0, 99999999998)

        # 配置输出文件名（节点113）
        video_id = generate_video_id()
        workflow['113']['inputs']['filename_prefix'] = f'video/{video_id}'

        execution = await execute(workflow, host, port, ctx=ctx)

        if not execution.outputs:
            raise Exception('No outputs from S2V workflow')

        url = execution.outputs[0]

        # 保存视频
        mime_type, width, height, duration, extension = await get_video_info_and_save(
            url, os.path.join(FILES_DIR, f'{video_id}')
        )
        filename = f'{video_id}.{extension}'
        return video_id, width, height, int(duration), filename


    async def _run_wan_s2v_workflow(
        self,
        user_prompt: str,
        input_image: str,
        input_audio: str,
        host: str,
        port: str,
        ctx: dict
    ) -> tuple[str, int, int, int, str]:
        """
        图片说话：根据音频和参考图生成口型同步的视频
        """
        import os
        import random
        import httpx
        workflow = copy.deepcopy(self.wan_s2v_workflow)

        # 配置正向提示词（节点6）
        workflow['6']['inputs']['text'] = user_prompt

        # 配置参考图片（节点52）- 使用 base64
        workflow['52']['class_type'] = 'ETN_LoadImageBase64'
        workflow['52']['inputs'] = workflow['52'].get('inputs', {})
        workflow['52']['inputs']['image'] = input_image
        print(f"✅ Configured image input (base64)")

        # 配置输入音频（节点58）- 上传到 ComfyUI 服务器
        audio_filename = input_audio
        if '.' not in input_audio:
            from services.db_service import db_service
            try:
                file_record = db_service.get_file(input_audio)
                if file_record and 'file_path' in file_record:
                    audio_filename = file_record['file_path']
                    print(f"🔍 Found audio in DB: {audio_filename}")
            except Exception as e:
                print(f"⚠️ DB lookup failed: {e}")

            if '.' not in audio_filename:
                for ext in ['mp3', 'wav', 'MP3', 'WAV', 'm4a', 'ogg']:
                    test_path = os.path.join(FILES_DIR, f'{input_audio}.{ext}')
                    if os.path.exists(test_path):
                        audio_filename = f'{input_audio}.{ext}'
                        print(f"✅ Found audio file: {audio_filename}")
                        break

        audio_file_path = os.path.join(FILES_DIR, audio_filename)
        if not os.path.exists(audio_file_path):
            raise Exception(f"Audio file not found: {audio_file_path}")

        print(f"📤 Uploading audio to ComfyUI: {audio_file_path}")

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_file_path, 'rb') as f:
                files = {'image': (audio_filename, f, 'audio/mpeg')}
                upload_url = f'http://{host}:{port}/upload/image'
                response = await client.post(upload_url, files=files)

                if response.status_code == 200:
                    result = response.json()
                    uploaded_filename = result.get('name', audio_filename)
                    print(f"✅ Audio uploaded to ComfyUI: {uploaded_filename}")
                    audio_filename = uploaded_filename
                else:
                    raise Exception(f"Failed to upload audio: {response.status_code}")

        workflow['58']['inputs']['audio'] = audio_filename
        print(f"✅ Configured audio input: {audio_filename}")

        # 配置随机种子
        import random
        workflow['3']['inputs']['seed'] = random.randint(0, 99999999998)
        workflow['79:77']['inputs']['seed'] = random.randint(0, 99999999998)
        workflow['85:77']['inputs']['seed'] = random.randint(0, 99999999998)

        # 配置输出文件名（节点113）
        video_id = generate_video_id()
        workflow['113']['inputs']['filename_prefix'] = f'video/{video_id}'

        print(f"🎬 Executing S2V workflow...")
        execution = await execute(workflow, host, port, ctx=ctx)

        if not execution.outputs:
            raise Exception('No outputs from S2V workflow')

        url = execution.outputs[0]

        # 保存视频
        mime_type, width, height, duration, extension = await get_video_info_and_save(
            url, os.path.join(FILES_DIR, f'{video_id}')
        )
        filename = f'{video_id}.{extension}'
        print(f"✅ Video generated: {filename}")
        return video_id, width, height, int(duration), filename

    async def _run_wan_t2v_workflow(self, user_prompt: str, host: str, port: str, ctx: dict) -> tuple[str, int, int, int, str]:
        """
        Run WAN text-to-video workflow
        """
        workflow = copy.deepcopy(self.wan_t2v_workflow)

        # Configure text prompt (node 16 - WanVideoTextEncode)
        # In the new workflow, the prompt is in inputs.positive_prompt
        workflow['16']['inputs']['positive_prompt'] = user_prompt
        
        # Configure seed (node 27 - WanVideoSampler)
        workflow['27']['inputs']['seed'] = random.randint(0, 99999999998)

        execution = await execute(workflow, host, port, ctx=ctx)

        if not execution.outputs:
            raise Exception('No outputs from WAN T2V workflow')

        url = execution.outputs[0]

        # Get video metadata and save
        video_id = generate_video_id()
        mime_type, width, height, duration, extension = await get_video_info_and_save(
            url, os.path.join(FILES_DIR, f'{video_id}')
        )
        filename = f'{video_id}.{extension}'
        return video_id, width, height, int(duration), filename

    async def _run_wan_i2v_workflow(self, user_prompt: str, input_image_base64: Optional[str], host: str, port: str, ctx: dict) -> tuple[str, int, int, int, str]:
        """
        Run WAN image-to-video workflow
        """
        workflow = copy.deepcopy(self.wan_i2v_workflow)

        if input_image_base64:
            # Configure input image (node 18 - LoadImage)
            # Note: We need to modify this to use base64 input instead of file loading
            # For now, we'll use a placeholder approach similar to flux-kontext
            workflow['122']['inputs']['image'] = input_image_base64
        else:
            # When no input image is provided, create a simple 1x1 pixel transparent PNG as placeholder
            placeholder_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQIHWNgAAIAAAUAAY27m/MAAAAASUVORK5CYII="
            workflow['122']['inputs']['image'] = placeholder_image
            print("🔍 DEBUG: Using placeholder image for WAN I2V workflow (no input image provided)")

        # Configure text prompt for I2V workflow
        # In I2V workflow, node 16 references node 46 (DeepTranslatorTextNode)
        # So we need to set the text in node 46
        workflow['98']['inputs']['text'] = user_prompt
        
        # Configure seed (node 27 - WanVideoSampler)
        workflow['27']['inputs']['seed'] = random.randint(0, 99999999998)

        execution = await execute(workflow, host, port, ctx=ctx)

        if not execution.outputs:
            raise Exception('No outputs from WAN I2V workflow')

        url = execution.outputs[0]

        # Get video metadata and save
        video_id = generate_video_id()
        mime_type, width, height, duration, extension = await get_video_info_and_save(
            url, os.path.join(FILES_DIR, f'{video_id}')
        )
        filename = f'{video_id}.{extension}'
        return video_id, width, height, int(duration), filename
