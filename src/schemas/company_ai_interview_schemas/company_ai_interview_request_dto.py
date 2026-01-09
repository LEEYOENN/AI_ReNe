from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any

class StartInterviewRequest(BaseModel):
    jobseeker_id: int
    company_id: int
    job_group_id: int

class EndInterviewRequest(BaseModel):
    session_id: str
    
# class InterviewAnswerRequest(BaseModel):
#     session_id: str
#     answer: str   

class EmailRequest(BaseModel):
    email: list[EmailStr]
    subject: str = "기업 AI 면접 분석 리포트 결과"
    html_content: str