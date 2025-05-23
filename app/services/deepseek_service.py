import os
import json
import requests
from app.schemas.video_script import VideoScript, Scene
from app.core.config import get_settings
from typing import List
import logging
import sys

# Cấu hình logging với UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DeepSeekService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.DEEPSEEK_API_KEY
        if not self.api_key or self.api_key == "your-deepseek-api-key-here":
            logger.warning("Using mock data for testing - DEEPSEEK_API_KEY not set or invalid")
            self.use_mock = True
        else:
            self.use_mock = False
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",  # Thêm referer cho OpenRouter
                "X-Title": "Architecture Design API"  # Thêm title cho OpenRouter
            }
        logger.info("DeepSeekService initialized")

    def _get_mock_script(self, topic: str, target_audience: str, duration: int) -> VideoScript:
        """Tạo dữ liệu mẫu cho testing"""
        return VideoScript(
            title=f"Kịch bản video về {topic}",
            description=f"Video giới thiệu về {topic} dành cho {target_audience}",
            target_audience=target_audience,
            total_duration=duration,
            scenes=[
                Scene(
                    scene_number=1,
                    description="Cảnh mở đầu giới thiệu tổng quan",
                    duration=20,
                    visual_elements=["Hình ảnh tổng thể", "Logo công ty"],
                    background_music="Nhạc nền nhẹ nhàng",
                    voice_over="Chào mừng đến với video giới thiệu về thiết kế nhà hiện đại"
                ),
                Scene(
                    scene_number=2,
                    description="Trình bày các điểm nổi bật",
                    duration=30,
                    visual_elements=["Hình ảnh chi tiết", "Biểu đồ thống kê"],
                    background_music="Nhạc nền sôi động",
                    voice_over="Hãy cùng khám phá những điểm nổi bật trong thiết kế"
                ),
                Scene(
                    scene_number=3,
                    description="Kết luận và call-to-action",
                    duration=10,
                    visual_elements=["Thông tin liên hệ", "QR code"],
                    background_music="Nhạc nền kết thúc",
                    voice_over="Liên hệ ngay với chúng tôi để được tư vấn chi tiết"
                )
            ]
        )

    def generate_video_script(self, topic: str, target_audience: str, duration: int) -> VideoScript:
        try:
            logger.info(f"Generating video script for topic: {topic}")
            
            if self.use_mock:
                logger.info("Using mock data for testing")
                return self._get_mock_script(topic, target_audience, duration)

            prompt = f"""
            Tạo một kịch bản video hấp dẫn về chủ đề: {topic}
            Đối tượng mục tiêu: {target_audience}
            Tổng thời lượng: {duration} giây

            Yêu cầu:
            1. Tạo các cảnh quay hấp dẫn và logic
            2. Mỗi cảnh cần có mô tả chi tiết
            3. Thêm các yếu tố hình ảnh cần thiết
            4. Đề xuất nhạc nền phù hợp
            5. Viết lời thuyết minh cho từng cảnh

            Format JSON:
            {{
                "title": "Tiêu đề video",
                "description": "Mô tả tổng quan",
                "target_audience": "Đối tượng mục tiêu",
                "total_duration": Tổng thời lượng,
                "scenes": [
                    {{
                        "scene_number": Số thứ tự cảnh,
                        "description": "Mô tả cảnh",
                        "duration": Thời lượng cảnh,
                        "visual_elements": ["Yếu tố hình ảnh 1", "Yếu tố hình ảnh 2"],
                        "background_music": "Đề xuất nhạc nền",
                        "voice_over": "Lời thuyết minh"
                    }}
                ]
            }}
            """

            payload = {
                "model": "deepseek/deepseek-chat:free",
                "messages": [
                    {"role": "system", "content": "Bạn là một chuyên gia viết kịch bản video chuyên nghiệp."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }

            logger.debug(f"Sending request to OpenRouter API with payload: {json.dumps(payload, ensure_ascii=False)}")
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            
            if response.status_code == 401:
                logger.error("Unauthorized: Invalid API key")
                raise ValueError("Invalid OpenRouter API key. Please check your API key in .env file")
            elif response.status_code != 200:
                logger.error(f"API request failed with status code: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                raise ValueError(f"OpenRouter API request failed: {response.text}")
                
            result = response.json()
            logger.info("Successfully received response from OpenRouter API")

            # Parse response và tạo VideoScript object
            script_data = result['choices'][0]['message']['content']
            try:
                # Tìm và trích xuất JSON từ response
                json_start = script_data.find('{')
                json_end = script_data.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = script_data[json_start:json_end]
                    data = json.loads(json_str)
                    
                    # Tạo danh sách Scene
                    scenes = []
                    for scene_data in data.get('scenes', []):
                        scene = Scene(
                            scene_number=scene_data['scene_number'],
                            description=scene_data['description'],
                            duration=scene_data['duration'],
                            visual_elements=scene_data['visual_elements'],
                            background_music=scene_data.get('background_music'),
                            voice_over=scene_data.get('voice_over')
                        )
                        scenes.append(scene)

                    # Tạo VideoScript object
                    script = VideoScript(
                        title=data['title'],
                        description=data['description'],
                        target_audience=data['target_audience'],
                        total_duration=data['total_duration'],
                        scenes=scenes
                    )
                    logger.info(f"Successfully generated video script with {len(scenes)} scenes")
                    return script
                else:
                    logger.error("No JSON found in response")
                    raise ValueError("No JSON found in response")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Response content: {script_data}")
                raise ValueError("Could not parse OpenRouter response")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise ValueError(f"Failed to connect to OpenRouter API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

    def enhance_script(self, script: VideoScript) -> VideoScript:
        """Cải thiện kịch bản với các đề xuất chi tiết hơn"""
        try:
            logger.info(f"Enhancing video script: {script.title}")
            
            if self.use_mock:
                logger.info("Using mock data for testing")
                # Thêm một số chi tiết vào script mẫu
                for scene in script.scenes:
                    scene.description += " (Đã được cải thiện)"
                    scene.visual_elements.append("Hiệu ứng chuyển cảnh mượt mà")
                return script

            prompt = f"""
            Cải thiện kịch bản video sau với các đề xuất chi tiết hơn:
            {script.json()}

            Yêu cầu:
            1. Thêm chi tiết cho mỗi cảnh
            2. Đề xuất các hiệu ứng chuyển cảnh
            3. Tối ưu thời lượng
            4. Thêm các yếu tố tương tác
            """

            payload = {
                "model": "deepseek/deepseek-chat:free",
                "messages": [
                    {"role": "system", "content": "Bạn là một chuyên gia chỉnh sửa kịch bản video."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }

            logger.debug(f"Sending enhancement request to OpenRouter API")
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            
            if response.status_code == 401:
                logger.error("Unauthorized: Invalid API key")
                raise ValueError("Invalid OpenRouter API key. Please check your API key in .env file")
            elif response.status_code != 200:
                logger.error(f"API request failed with status code: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                raise ValueError(f"OpenRouter API request failed: {response.text}")
                
            result = response.json()
            logger.info("Successfully received enhancement response from OpenRouter API")

            # Parse response và cập nhật VideoScript object
            script_data = result['choices'][0]['message']['content']
            try:
                json_start = script_data.find('{')
                json_end = script_data.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = script_data[json_start:json_end]
                    data = json.loads(json_str)
                    
                    # Cập nhật script với dữ liệu mới
                    script.title = data.get('title', script.title)
                    script.description = data.get('description', script.description)
                    script.total_duration = data.get('total_duration', script.total_duration)
                    
                    # Cập nhật scenes
                    if 'scenes' in data:
                        scenes = []
                        for scene_data in data['scenes']:
                            scene = Scene(
                                scene_number=scene_data['scene_number'],
                                description=scene_data['description'],
                                duration=scene_data['duration'],
                                visual_elements=scene_data['visual_elements'],
                                background_music=scene_data.get('background_music'),
                                voice_over=scene_data.get('voice_over')
                            )
                            scenes.append(scene)
                        script.scenes = scenes
                    
                    logger.info(f"Successfully enhanced video script with {len(script.scenes)} scenes")
                    return script
                else:
                    logger.error("No JSON found in enhancement response")
                    raise ValueError("No JSON found in response")
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Response content: {script_data}")
                raise ValueError("Could not parse OpenRouter response")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            raise ValueError(f"Failed to connect to OpenRouter API: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise 