from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class InterviewResponse(BaseModel):
    message: str = Field(..., description="Response 메시지 (예: 200 OK)")
    session_id: str # 세션 ID
    current_turn: int # 현재 면접 턴수
    interview_stage: str # 인터뷰 단계
    ai_message: str  # 면접관(AI)의 질문 또는 안내
    ai_audio_base64: Optional[str] = None # 오디오 파일(Base64 인코딩): TTS로 변환된 파일
    status: str   # 'interview', 'done', 'error'
    interview_result_id: Optional[int] = None

class SkillDetailResponse(BaseModel):
    skill_name: str
    score: int
    reason: str

class QnAFeedback(BaseModel):
    question: str
    user_answer: str
    better_answer: str
    score: int

class InterviewResultResponse(BaseModel):
    message: str = Field(..., description="API 응답 메시지, 예: 200 OK")
    interview_id: int = Field(..., description="인터뷰 ID")
    session_id: str = Field(..., description="면접 세션 ID")
    
    # DB Entity에서 추출한 필드들
    jobseeker_id: int = Field(..., description="구직자 ID")
    job_group_id: int = Field(..., description="직군 ID")
    jobseeker_name: Optional[str] = Field(None, description="구직자 이름")
    company_name: Optional[str] = Field(None, description="기업 이름")
    job_group_name: Optional[str] = Field(None, description="직군 이름")
    jobseeker_email: Optional[str] = Field(None, description="구직자 이메일")

    report: str = Field(..., description="상세 면접 리포트")
    summary: str = Field(..., description="면접 한줄 요약")
    total_score: float = Field(..., description="종합 점수")
    
    # DB의 JSON 컬럼 대응 (List[Dict] 또는 위에서 정의한 SkillDetailResponse 리스트)
    skills_evaluation: List[Dict[str, Any]] = Field(..., description="기술 스택별 상세 평가")
    
    ai_result: str = Field(..., description="AI 합불 결과 (PASS/HOLD/FAIL)")
    best_answer: str = Field(..., description="최고의 답변")
    worst_answer: str = Field(..., description="최악의 답변")
    total_advice: str = Field(..., description="종합 피드백/조언")
    better_answer_list: List[QnAFeedback] = Field(..., description="면접 질문, 면접자 답변, 보완된 답변, 점수 리스트")
    end_time: Optional[str] = Field(None, description="면접 종료 시간 (YYYY.MM.DD HH:MM)")