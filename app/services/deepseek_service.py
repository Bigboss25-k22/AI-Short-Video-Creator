import os
import json
import requests
from app.schemas.video_script import VideoScript, Scene
from app.core.config import get_settings
from typing import List
import logging
import sys
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import datetime
import enum

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
        
        # Kiểm tra API key có hợp lệ không
        if not self.api_key or self.api_key == "" or self.api_key == "your-deepseek-api-key-here":
            logger.warning("DEEPSEEK_API_KEY not set or invalid - Using mock data for testing")
            self.use_mock = True
            self.api_url = None
            self.headers = None
            self.session = None
        else:
            logger.info("DEEPSEEK_API_KEY found - Using OpenRouter API")
            self.use_mock = False
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"
            self.headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Architecture Design API"
            }
            # Cấu hình session với retry mechanism
            self.session = requests.Session()
            retries = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[500, 502, 503, 504]
            )
            self.session.mount('https://', HTTPAdapter(max_retries=retries))
            self.session.mount('http://', HTTPAdapter(max_retries=retries))
        
        logger.info("DeepSeekService initialized")

    def _get_mock_script(self, topic: str, target_audience: str, duration: int) -> VideoScript:
        """Tạo dữ liệu mẫu cho testing"""
        return VideoScript(
            title=f"Kịch bản video về {topic}",
            description=f"Video chia sẻ về {topic} dành cho {target_audience}",
            target_audience=target_audience,
            total_duration=duration,
            scenes=[
                Scene(
                    scene_number=1,
                    description="Cảnh mở đầu - Giới thiệu chủ đề thi cử",
                    duration=20,
                    visual_elements="A high school classroom with wooden desks arranged in rows. Natural light streams through large windows on the left side. The walls are painted light blue with motivational posters. A whiteboard at the front displays exam schedules. Students in school uniforms sit at their desks, some looking nervous, others confident. The atmosphere is tense but hopeful.",
                    background_music="Nhạc nền nhẹ nhàng, tạo cảm giác lo lắng nhưng hy vọng",
                    voice_over="Kỳ thi trung học phổ thông - một bước ngoặt quan trọng trong cuộc đời mỗi học sinh"
                ),
                Scene(
                    scene_number=2,
                    description="Cảnh chính - Chia sẻ về thất bại và bài học",
                    duration=30,
                    visual_elements="A student's bedroom with study materials scattered on a wooden desk. A laptop screen shows exam results with disappointing scores. The room has warm lighting from a desk lamp. The student sits on the bed, looking thoughtful but not defeated. Books and notebooks are stacked neatly on shelves. A motivational quote is pinned to the wall.",
                    background_music="Nhạc nền sâu lắng, phản ánh cảm xúc suy tư",
                    voice_over="Nhưng điều quan trọng không phải là điểm số, mà là những bài học quý giá từ thất bại"
                ),
                Scene(
                    scene_number=3,
                    description="Cảnh kết thúc - Thông điệp tích cực",
                    duration=10,
                    visual_elements="A bright, modern study room with a student sitting at a clean desk, surrounded by organized study materials. Sunlight pours through a large window, creating a warm, optimistic atmosphere. The student is smiling and looking confident. A calendar on the wall shows future exam dates. Success is clearly within reach.",
                    background_music="Nhạc nền lạc quan, truyền cảm hứng",
                    voice_over="Hãy nhớ rằng, mỗi thất bại là một bước đệm để thành công"
                )
            ]
        )

    def generate_video_script(self, topic: str, target_audience: str, duration: int) -> VideoScript:
        try:
            logger.info(f"Generating video script for topic: {topic}")

            if self.use_mock:
                logger.info("Using mock data for testing")
                return self._get_mock_script(topic, target_audience, duration)

            # Kiểm tra lại trước khi gọi API
            if not self.api_key or self.api_key == "":
                logger.warning("API key is empty, falling back to mock data")
                return self._get_mock_script(topic, target_audience, duration)

            # Bước 1: Tạo nội dung kịch bản tổng thể
            content_prompt = f"""
            Tạo một kịch bản video hấp dẫn về chủ đề: {topic}
            Đối tượng mục tiêu: {target_audience}
            Tổng thời lượng: {duration} giây

            Yêu cầu:
            1. Viết một bài viết hoàn chỉnh về chủ đề này
            2. Bài viết phải có cấu trúc rõ ràng với các phần:
               - Mở đầu: Giới thiệu chủ đề
               - Thân bài: Phát triển các ý chính
               - Kết luận: Tổng kết và call-to-action
            3. Mỗi phần cần có nội dung chi tiết và hấp dẫn
            4. Sử dụng ngôn ngữ phù hợp với đối tượng mục tiêu
            """

            content_payload = {
                "model": "deepseek/deepseek-chat:free",
                "messages": [
                    {"role": "system", "content": "Bạn là một chuyên gia viết kịch bản video chuyên nghiệp."},
                    {"role": "user", "content": content_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }


            content_response = self.session.post(self.api_url, headers=self.headers, json=content_payload, timeout=60)

            # Kiểm tra response có rỗng không
            if not content_response.text or content_response.text.strip() == "":
                logger.error("OpenRouter returned empty response - likely API key issue")
                logger.error("Falling back to mock data")
                return self._get_mock_script(topic, target_audience, duration)
            
            if content_response.status_code != 200:
                logger.error(f"Content generation failed: {content_response.text}")
                raise ValueError(f"Failed to generate script content: {content_response.text}")

            script_content = content_response.json()['choices'][0]['message']['content']
            logger.info("Successfully generated overall script content")

            # Bước 2: Tách nội dung thành các cảnh
            scenes_prompt = f"""
            Dựa vào nội dung kịch bản sau, hãy tách thành các cảnh quay phù hợp:
            {script_content}

            Yêu cầu:
            1. Tách nội dung thành các cảnh logic và hấp dẫn
            2. Mỗi cảnh cần có mô tả chi tiết về:
               - Không gian và bối cảnh:
                 + Vị trí diễn ra cảnh (phòng khách, phòng ngủ, sân trường, etc.)
                 + Mô tả chi tiết không gian (kích thước, màu sắc tường, sàn, trần)
                 + Các đồ vật trong không gian (bàn, ghế, tủ, etc.)
                 + Vị trí và trạng thái của các đồ vật
               - Ánh sáng và màu sắc:
                 + Nguồn sáng (ánh sáng tự nhiên, đèn điện, etc.)
                 + Hướng chiếu sáng
                 + Màu sắc và cường độ ánh sáng
                 + Bóng đổ và hiệu ứng ánh sáng
               - Nhân vật và trang phục:
                 + Vị trí của nhân vật trong khung hình
                 + Tư thế và biểu cảm
                 + Trang phục chi tiết (màu sắc, kiểu dáng)
                 + Các phụ kiện đi kèm
               - Thời tiết và thời gian:
                 + Thời điểm trong ngày
                 + Điều kiện thời tiết
                 + Các yếu tố thời tiết đặc biệt (mưa, nắng, etc.)

            3. Thời lượng phù hợp (tổng {duration} giây)
            4. Mô tả chi tiết cho việc tạo hình ảnh (visual_elements) phải là một đoạn văn mô tả đầy đủ về không gian, ánh sáng, nhân vật và thời tiết BẰNG TIẾNG ANH
            5. Đề xuất nhạc nền phù hợp với cảm xúc của cảnh
            6. Lời thuyết minh phù hợp

            Format JSON:
            {{
                "title": "Tiêu đề video",
                "description": "Mô tả tổng quan",
                "target_audience": "{target_audience}",
                "total_duration": {duration},
                "scenes": [
                    {{
                        "scene_number": Số thứ tự cảnh,
                        "description": "Mô tả ngắn gọn về cảnh",
                        "duration": Thời lượng cảnh,
                        "visual_elements": "Detailed description of space, lighting, characters and weather in English for image generation",
                        "background_music": "Đề xuất nhạc nền phù hợp với cảm xúc",
                        "voice_over": "Lời thuyết minh"
                    }}
                ]
            }}
            """

            scenes_payload = {
                "model": "deepseek/deepseek-chat:free",
                "messages": [
                    {"role": "system", "content": "Bạn là một chuyên gia phân cảnh video và thiết kế hình ảnh, có khả năng tạo ra những mô tả chi tiết và sinh động về bối cảnh, ánh sáng, và nhân vật."},
                    {"role": "user", "content": scenes_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }

            logger.info("Splitting content into scenes...")
            scenes_response = self.session.post(self.api_url, headers=self.headers, json=scenes_payload, timeout=60)

            if scenes_response.status_code != 200:
                logger.error(f"Scene generation failed: {scenes_response.text}")
                raise ValueError(f"Failed to generate scenes: {scenes_response.text}")

            scenes_data = scenes_response.json()['choices'][0]['message']['content']
            logger.info("Successfully generated scenes")

            # Parse response và tạo VideoScript object
            try:
                json_start = scenes_data.find('{')
                json_end = scenes_data.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = scenes_data[json_start:json_end]
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
                logger.error(f"Response content: {scenes_data}")
                raise ValueError("Could not parse scenes response")

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

            def default_serializer(obj):
                if isinstance(obj, (datetime.datetime, datetime.date)):
                    return obj.isoformat()
                if isinstance(obj, enum.Enum):
                    return obj.value
                raise TypeError(f"Type {type(obj)} not serializable")

            prompt = f"""
            Cải thiện kịch bản video sau với các đề xuất chi tiết hơn:
            {json.dumps(script.dict(by_alias=True, exclude_unset=True), ensure_ascii=False, indent=2, default=default_serializer)}

            Yêu cầu:
            1. Thêm chi tiết cho mỗi cảnh
            2. Đề xuất các hiệu ứng chuyển cảnh
            3. Tối ưu thời lượng
            4. Thêm các yếu tố tương tác
            5. Chỉ trả về kết quả ở dạng JSON, không thêm bất kỳ giải thích nào.
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
            response = self.session.post(self.api_url, headers=self.headers, json=payload, timeout=60)

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