from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import logging
from typing import List
from app.schemas.content_suggestion import VideoInfo
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleSearchService:
    def __init__(self):
        self.setup_driver()

    def setup_driver(self):
        """Thiết lập Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Chạy ẩn
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def search_videos(self, keyword: str, max_results: int = 10) -> List[VideoInfo]:
        """
        Tìm kiếm video trên Google theo từ khóa
        """
        try:
            # Tạo URL tìm kiếm Google với filter video
            search_url = f"https://www.google.com/search?q={keyword}&tbm=vid"
            self.driver.get(search_url)

            # Đợi cho các kết quả video xuất hiện
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
            )

            # Lấy HTML của trang
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # Tìm tất cả các kết quả video
            video_results = soup.find_all("div", class_="g")[:max_results]
            videos = []

            for result in video_results:
                try:
                    # Lấy thông tin video
                    title_element = result.find("h3")
                    link_element = result.find("a")
                    description_element = result.find("div", class_="VwiC3b")
                    thumbnail_element = result.find("img")

                    if title_element and link_element:
                        video = VideoInfo(
                            title=title_element.text,
                            description=description_element.text if description_element else "",
                            url=link_element["href"],
                            thumbnail_url=thumbnail_element["src"] if thumbnail_element else None,
                            platform="google",
                            published_at=datetime.now(),  # Google không cung cấp thời gian chính xác
                            channel_name="",  # Google không cung cấp tên kênh
                        )
                        videos.append(video)
                except Exception as e:
                    logger.error(f"Error parsing video result: {e}")
                    continue

            return videos

        except Exception as e:
            logger.error(f"An error occurred while searching Google: {e}")
            return []
        finally:
            self.driver.quit()

    def __del__(self):
        """Đảm bảo đóng WebDriver khi đối tượng bị hủy"""
        try:
            self.driver.quit()
        except:
            pass 