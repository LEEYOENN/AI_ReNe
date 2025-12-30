from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from api.deps import get_db
from src.services.company_ai_interview_service.company_ai_interview_service import CompanyAIInterviewService
from src.schemas.company_ai_interview_schemas import company_ai_interview_request_dto, company_ai_interview_response_dto

router = APIRouter(prefix="/company/ai-interview", tags=["Company AI Interview"])

@router.post("/start", response_model=company_ai_interview_response_dto.InterviewResponse)
async def start_interview(
        request: company_ai_interview_request_dto.StartInterviewRequest,
        db: Session = Depends(get_db)
):
    """
    기업 AI 면접을 시작합니다.
    """
    service = CompanyAIInterviewService(db)
    return await service.start_new_interview(request)

@router.post("/chat/voice", response_model=company_ai_interview_response_dto.InterviewResponse)
async def chat_interview(
    # JSON DTO 대신 Form 데이터로 개별 필드를 받습니다.
    session_id: str = Form(..., description="면접 세션 ID"),
    file: UploadFile = File(..., description="사용자 음성 답변 파일"),
    db: Session = Depends(get_db)
):
    """
    [음성] 사용자의 음성 답변을 받아 STT -> Agent -> TTS로 답변을 제출하고 
    다음 면접관의 반응을 음성으로 보냅니다.
    """
    service = CompanyAIInterviewService(db)
    return await service.process_voice_answer(session_id, file)

@router.get("/report/{interview_id}", response_model=company_ai_interview_response_dto.InterviewResultResponse)
async def get_interview_result_by_id(
    interview_id: int,
    db: Session = Depends(get_db)
):
    service = CompanyAIInterviewService(db)
    return await service.get_interview_result_by_interview_id(interview_id)

@router.post("/force-end", response_model=company_ai_interview_response_dto.InterviewResponse)
async def force_end_interview(
    request: company_ai_interview_request_dto.EndInterviewRequest,
    db: Session = Depends(get_db)
):
    service = CompanyAIInterviewService(db)
    return await service.force_end_interview(request.session_id)