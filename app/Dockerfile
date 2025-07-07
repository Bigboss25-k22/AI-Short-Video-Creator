# Sử dụng image Python chính thức
FROM python:3.10-slim

# Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Tạo thư mục làm việc
WORKDIR /app

# Cài đặt các dependencies hệ thống (nếu cần, ví dụ: gcc, libpq-dev cho PostgreSQL)
RUN apt-get update && \
    apt-get install -y gcc && \
    apt-get clean

# Copy file requirements.txt vào container
COPY Project/requirements.txt .

# Cài đặt các dependencies Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY Project/app /app/app

# Expose port (thay đổi nếu bạn dùng port khác)
EXPOSE 8000

# Lệnh chạy ứng dụng (giả sử dùng uvicorn và file main.py)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]