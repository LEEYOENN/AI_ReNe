#모듈 정의 : ElevenLabs API 기반 고품질 TTS 기능 제공 - Service Class
#연결 모듈 : src/services/interview_service/interview_service.py (Service)
import os, sys
import io
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from pydub import AudioSegment
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from core.config import settings
from dotenv import load_dotenv

load_dotenv()

class ElevenLabsTTSService:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
    
        if not self.api_key:
            print("ELEVENLABS_API_KEY가 설정되지 않았습니다.")
        
        self.client = ElevenLabs(api_key=self.api_key)
        #목소리
        self.voice_id = "gJSDQIpSQ56NBGhorBfg" # 목소리 좋은 유튜버 목소리
        # "v1jVu1Ky28piIPEJqRrm" # 젠틀하고 낮은 다큐멘터리 남성 
        #"pb3lVZVjdFWbkhPKlelB" # 중년 목소리 
        # 젊은 남성 목소리 - "OEaq3WGNtNvFJ5co9mJE"

        # 한글 지원 모델
        self.model_id = "eleven_multilingual_v2"

    def speak(self, text: str) -> bytes:
        """
        텍스트를 받아서 ElevenLabs API 호출하고 오디오 bytes로 반환합니다.
        """
        try:
            if not text:
                print("TTS를 진행할 텍스트가 없습니다.")
                return None
            
            # ElevenLabs API 호출
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model_id,
                voice_settings=VoiceSettings(stability=0.1, similarity_boost=0.75),
            )
            
            mp3_data = b"".join(audio_generator)

            audio_segment = AudioSegment.from_mp3(io.BytesIO(mp3_data))
            
            wav_buffer = io.BytesIO()

            audio_segment.export(wav_buffer, format="wav")
            
            print(f"변환 완료: MP3({len(mp3_data)} bytes) -> WAV({wav_buffer.getbuffer().nbytes} bytes)")
            
            return wav_buffer.getvalue()
        
        except Exception as e:
            print(f"ElevenLabs TTS 변환 중 오류: {e}")
            return None

try:
    tts_service = ElevenLabsTTSService()
except Exception as e:
    print(f"ElevenLabs TTS 로딩 실패: {e}")   






