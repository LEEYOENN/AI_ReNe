from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

current_path = Path(__file__).resolve()
PROJECT_ROOT = current_path.parent.parent.parent
WHISPER_KOREAN_MODEL_PATH_OBJ = PROJECT_ROOT / "data" / "models" / "whisper_large_v3_turbo_korean"
WHISPER_LARGE_V3_MODEL_PATH_OBJ = PROJECT_ROOT / "data" / "models" / "whisper_large_v3"


class Settings(BaseSettings):
    """
    서비스의 환경 변수를 관리하는 설정 클래스
    .env 파일로부터 값을 자동으로 로드합니다.
    """

    OPENAI_API_KEY: str

    STT_PROVIDER: str = "naver"
    TTS_PROVIDER: str = "naver"

    LANGSMITH_TRACING: bool
    LANGSMITH_ENDPOINT: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str

    # Naver Cloud Platform (NCP)
    NCP_CLIENT_ID: str
    NCP_SECRET_KEY: str
    CLOVA_SPEECH_INVOKE_URL: str
    CLOVA_SPEECH_SECRET_KEY: str

    # Google Sheets
    DAILY_NOTES_GOOGLE_SHEET_ID: str
    GOOGLE_SHEETS_CREDENTIALS_PATH: str

    # MySQL
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = 3306
    DB_NAME: str

    # Whisper
    WHISPER_KOREAN_MODEL_PATH: str = str(WHISPER_KOREAN_MODEL_PATH_OBJ)
    WHISPER_LARGE_V3_MODEL_PATH: str = str(WHISPER_LARGE_V3_MODEL_PATH_OBJ)

    # ElevenLabs
    ELEVENLABS_API_KEY: str

    # VetorDB collection name
    COMPANY_COLLECTION_NAME: str = "company_recruit_data"
    JOBSEEKER_COLLECTION_NAME: str = "jobseeker_data"

    MAIL_USERNAME: str
    MAIL_PASSWORD: str       # 2단계 인증 시 '앱 비밀번호'
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool
    USE_CREDENTIALS: bool
    VALIDATE_CERTS: bool

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env에 정의되지 않은 변수가 있어도 무시함 (에러 방지)
    )


try:
    settings = Settings()
except Exception as e:
    print(f"환경 변수 로딩 실패: .env 파일을 확인하세요. 오류: {e}")
