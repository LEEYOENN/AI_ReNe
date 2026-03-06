# uv pip install torch torchvision torchaudio --torch-backend=cu126
import torch
import numpy as np
import os, sys
import io
import tempfile
from faster_whisper import WhisperModel
from dotenv import load_dotenv
load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from core.config import settings

class FasterWhisperService:
    """
    Faster Whisper 전용 STT Service
    Singleton 패턴 적용
    최초 한 번 STT 모델 로딩
    """
    _instance = None # Singleton - 처음 한 번만 객체 생성

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FasterWhisperService, cls).__new__(cls) # STTService 객체 생성
            cls._instance.initialize_model() # 모델 로딩 함수 실행
        return cls._instance

    # STT 모델 로딩 함수
    def initialize_model(self):
        print("Faster-Whisper (Large-v3) STT 모델 로딩 중...")
        # if torch.backends.mps.is_available():
        #     device = torch.device("mps")
        # else:
        #     device = torch.device("cpu")
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        compute_type = "float16" if device == 'cuda' else "int8"
        # huggingface의 복잡한 모델 사용 과정을 pipeline으로 자동화 (전처리(tensor로 변환) - 모델 추론 - 후처리(decoding))
        self.model = WhisperModel(
            model_size_or_path="deepdml/faster-whisper-large-v3-turbo-ct2",
            device=device,
            compute_type=compute_type
        )
        # [Warm-up] 초기화 시 더미 데이터로 1회 추론 실행 -> 첫번째 요청이 느려지지 않게
        print("[Faster-Whisper Warm-up] 노이즈 데이터로 공회전 실행 중...")
        dummy_audio = np.random.normal(0, 1, 16000).astype(np.float32)
        try:
            self.model.transcribe(dummy_audio, language="ko")
            print(f"Faster-Whisper 모델 준비 완료 (Device: {device})")
        except Exception as e:
            print(f"Warm-up 실패 (무시 가능)")


        print(f"Faster-Whisper 모델 로딩 완료 (Device: {device})")

    def transcribe(self, audio_bytes: bytes) -> str:
        """
        바이너리 데이터를 메모리에 적재 WhisperModel.transcribe로 로드하여 STT 수행
        [최적화 포인트]
        1. io.BytesIO 사용 (Disk I/O 제거)
        """
        try:
            # # 안전하게 임시 파일 생성 (확장자 wav 명시 - pcm_to_wav_bytes가 wav 포맷을 반환하므로)
            # with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            #     temp_file.write(audio_bytes)
            #     temp_path = temp_file.name

            # print(f"임시 파일 생성됨: {temp_path}")
            # print(f"파일 크기: {os.path.getsize(temp_path)} bytes")
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"

            # 추론 (librosa 불필요 - 내부적으로 ffmpeg를 사용)
            segments, info = self.model.transcribe(
                audio_file,
                language='ko',
                beam_size=1, # 속도가 최우선이면 1로 설정
                vad_filter=True, # 음성이 없는 구간을 필터링
                vad_parameters=dict(min_silence_duration_ms=500) # 500ms(0.5초) 이상의 침묵이 감지되어야 문장을 끊거나 구간을 나눈다
            )

            # STT 모델로 한국어로 변환
            text_result = "".join([segment.text for segment in segments])

            # 결과 서빙
            return text_result.strip()
        
        except Exception as e:
            print(f"STT 변환 중 에러 발생: {e}")
            import traceback
            print(traceback.print_exc())  # 상세한 에러 로그 출력
            return ""

        # finally:
        #     # 임시 파일 삭제
        #     if temp_path and os.path.exists(temp_path):
        #         try:
        #             os.remove(temp_path)
        #         except Exception as e:
        #             print(f"임시 파일 삭제 실패: {e}")

# global STTService instance 생성 (import 용)
try:
    stt_service = FasterWhisperService()
except Exception as e:
    print(f"Faster-Whisper 모델 로딩 실패: {e}")



    