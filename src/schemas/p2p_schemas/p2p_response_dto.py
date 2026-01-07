from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class P2PChunkResponseDto(BaseModel):
    session_id: str
    turn_number: int
    text: str
    status: str = "success"

class P2PReportResponseDto(BaseModel):
    session_id: str
    thinking_process: str
    human_report: str
    update_data: Dict[str, Any]
    raw_response: Optional[str] = None

class QnAFeedback(BaseModel):
    question: str
    user_answer: str
    better_answer: str
    score: int

class P2PInterviewResultResponse(BaseModel):
    message: str = Field(..., description="API 응답 메시지")
    interview_id: int = Field(..., description="인터뷰 ID")
    jobseeker_id: int = Field(..., description="구직자 ID")
    job_group_id: int = Field(..., description="직군 ID")
    jobseeker_name: Optional[str] = Field(None, description="구직자 이름")
    job_group_name: Optional[str] = Field(None, description="직군 이름")
    
    report: str = Field(..., description="상세 면접 리포트")
    summary: str = Field(..., description="면접 한줄 요약")
    total_score: float = Field(..., description="종합 점수")
    
    skills_evaluation: List[Dict[str, Any]] = Field(..., description="기술 스택별 상세 평가")
    
    ai_result: Optional[str] = Field(None, description="AI 합불 결과 (PASS/HOLD/FAIL)")
    best_answer: Optional[str] = Field(None, description="최고의 답변")
    worst_answer: Optional[str] = Field(None, description="최악의 답변")
    total_advice: Optional[str] = Field(None, description="종합 피드백/조언")
    better_answer_list: List[QnAFeedback] = Field(..., description="면접 질문, 면접자 답변, 보완된 답변, 점수 리스트")
    end_time: Optional[str] = Field(None, description="면접 종료 시간 (YYYY.MM.DD HH:MM)")