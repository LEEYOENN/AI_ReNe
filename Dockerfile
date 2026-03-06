# 1. Base Image (Python 3.11)
FROM python:3.11-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 시스템 필수 패키지 설치 (오디오 처리를 위한 ffmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 4. 패키지 매니저 uv 설치
RUN pip install --no-cache-dir uv

# 5. 의존성 설치
COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

# 6. 소스 코드 복사
COPY . .

# 7. FastAPI 포트 노출
EXPOSE 8000

# 8. 서버 실행
CMD ["uvicorn", "src.api.endpoints.main:app", "--host", "0.0.0.0", "--port", "8000"]
