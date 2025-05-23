import replicate
import os
from typing import Optional
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class ImageGenerationService:
    def __init__(self):
        settings = get_settings()
        self.api_token = settings.REPLICATE_API_TOKEN
        if not self.api_token:
            raise ValueError("REPLICATE_API_TOKEN is not set in settings")
        
        # Khởi tạo client Replicate
        self.client = replicate.Client(api_token=self.api_token)
        
        # Model ID cho Stable Diffusion
        self.model_id = settings.REPLICATE_MODEL_ID or "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"

    def generate_image(self, prompt: str, width: int = 1024, height: int = 768) -> Optional[str]:
        """
        Tạo hình ảnh từ prompt sử dụng Replicate API
        
        Args:
            prompt (str): Mô tả chi tiết về hình ảnh cần tạo
            width (int): Chiều rộng hình ảnh
            height (int): Chiều cao hình ảnh
            
        Returns:
            str: URL của hình ảnh được tạo, hoặc None nếu có lỗi
        """
        try:
            # Thêm các tham số để cải thiện chất lượng hình ảnh
            output = self.client.run(
                self.model_id,
                input={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_outputs": 1,
                    "scheduler": "K_EULER",
                    "num_inference_steps": 50,
                    "guidance_scale": 7.5,
                    "negative_prompt": "blurry, low quality, distorted, deformed",
                    "prompt_strength": 0.8,
                    "refine": "expert_ensemble_refiner",
                    "high_noise_frac": 0.8
                }
            )
            
            if output and isinstance(output, list) and len(output) > 0:
                # Xử lý FileOutput object
                image_output = output[0]
                if hasattr(image_output, 'url'):
                    return image_output.url
                elif isinstance(image_output, str):
                    return image_output
                else:
                    logger.error(f"Unexpected output type: {type(image_output)}")
                    return None
            return None
            
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None 