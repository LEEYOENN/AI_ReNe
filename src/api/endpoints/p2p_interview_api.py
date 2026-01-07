from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from fastapi.responses import FileResponse, Response
from typing import Optional
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가 (src 상위 폴더)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.pdf_utils import convert_pdf_to_image
from src.services.p2p_service import p2p_service
from src.schemas.p2p_schemas.p2p_response_dto import P2PChunkResponseDto, P2PReportResponseDto, P2PInterviewResultResponse
from src.models.interview import NonContactInterview
from src.models.user import Jobseeker, JobGroup, Company
from src.core.database import SessionLocal

p2p_router = APIRouter(prefix="/p2p", tags=["P2P Interview"])

@p2p_router.get("/audio-chunk1")
async def get_p2p_audio_chunk1():
    """
    [P2P] 검증 결과 요약 PDF 반환
    """
    # 임시: 결과 파일 반환
    base_path = os.path.join("data", "p2p_sessions")
    file1 = os.path.join(base_path, "검증 결과 요약.pdf")
    
    if not os.path.exists(file1):
        raise HTTPException(status_code=404, detail="File not found")
            
    return FileResponse(file1, media_type='application/pdf', filename="검증 결과 요약.pdf")


@p2p_router.get("/audio-chunk2")
async def get_p2p_audio_chunk2():
    """
    [P2P] 면접 결과 요약 PNG 반환
    """
    try:
        # 1. 보고서 생성 (DB 저장)
        interview_id = await p2p_service.finalize_p2p_interview()
        
        # 2. 결과 반환 (JSON)
        return {"message": "Interview finalized", "interview_id": interview_id}
        
    except Exception as e:
        print(f"Error in audio-chunk2: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@p2p_router.post("/audio-check", response_model=P2PChunkResponseDto)
async def upload_p2p_session_audio(
    file: UploadFile = File(...),
    speaker_role: str = Form(...),
    jobseeker_id: Optional[int] = Form(None)
):
    """
    [P2P] 실시간 오디오 청크 업로드 (PCM)
    - 화자별 버퍼링 및 STT 처리 (단일 세션)
    - jobseeker_id를 받아 세션에 매핑
    """
    # jobseeker_id를 문자열로 변환하여 서비스에 전달
    user_identifier = str(jobseeker_id) if jobseeker_id else None

    return await p2p_service.process_p2p_audio_chunk(file, speaker_role, user_identifier)

@p2p_router.get("/report")
async def generate_p2p_report():
    """
    [P2P] 인터뷰 종료 및 보고서 생성 (P2P Auditor Agent)
    - DB 저장 후 ID 반환
    """
    try:
        interview_id = await p2p_service.finalize_p2p_interview()
        return {"message": "Report generated", "interview_id": interview_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@p2p_router.get("/result/{interview_id}", response_model=P2PInterviewResultResponse)
async def get_p2p_interview_result(interview_id: int):
    """
    [P2P] 저장된 면접 결과 조회 (Web View용)
    """
    db = SessionLocal()
    try:
        # Join query to get names
        result = (
            db.query(
                NonContactInterview,
                Jobseeker.name.label("jobseeker_name"),
                JobGroup.name.label("job_group_name")
            )
            .join(Jobseeker, NonContactInterview.jobseeker_id == Jobseeker.id)
            .join(JobGroup, NonContactInterview.job_group_id == JobGroup.id)
            .filter(NonContactInterview.id == interview_id)
            .first()
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Interview result not found")
            
        interview, jobseeker_name, job_group_name = result
        
        formatted_end_time = None
        if interview.end_time:
            formatted_end_time = interview.end_time.strftime("%Y.%m.%d %H:%M")
            
        return P2PInterviewResultResponse(
            message="200 OK",
            interview_id=interview.id,
            jobseeker_id=interview.jobseeker_id,
            job_group_id=interview.job_group_id,
            jobseeker_name=jobseeker_name,
            job_group_name=job_group_name,
            report=interview.report or "",
            summary=interview.summary or "",
            total_score=interview.total_score or 0.0,
            skills_evaluation=interview.skills_evaluation or [],
            ai_result=interview.ai_result or "HOLD",
            best_answer=interview.best_answer or "",
            worst_answer=interview.worst_answer or "",
            total_advice=interview.total_advice or "",
            better_answer_list=interview.better_answer_list or [],
            end_time=formatted_end_time
        )
    finally:
        db.close()

@p2p_router.post("/reset")
async def reset_p2p_session_endpoint():
    """
    [P2P] 세션 초기화
    - 이전 면접 기록(오디오 버퍼, 스크립트 등)을 모두 삭제합니다.
    - 새로운 면접을 시작하기 전에 호출해야 합니다.
    """
    try:
        p2p_service.reset_p2p_session()
        return {"message": "P2P session has been reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset session: {str(e)}")