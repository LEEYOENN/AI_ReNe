from pydantic import BaseModel, Field
from typing import Optional

class DashboardInterviewItemResponse(BaseModel):
    interview_id: int = Field(..., description="면접 결과 ID (상세보기 클릭용)")
    
    # 구직자 정보 (Repo에서 Join으로 가져온 값)
    jobseeker_name: str = Field(..., description="구직자 이름")
    jobseeker_email: str = Field(..., description="구직자 이메일 (연락용)")
    
    # 핵심 요약 정보
    total_score: float = Field(..., description="종합 점수")
    ai_result: str = Field(..., description="합불 결과 (PASS/WEAK/FAIL)")
    summary: str = Field(..., description="면접 한 줄 요약")
    
    # [추천] 정렬이나 필터링을 위해 필요
    created_at: str = Field(..., description="면접 응시 일자 (YYYY.MM.DD)")