from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from sqlalchemy.orm import Session
import os
from uuid import uuid4
from typing import Optional, Union

from api.deps import get_db
from src.models.user import Jobseeker
from services.file_upload_service.seeker_file_upload_service import process_file_upload
from services.file_upload_service.company_file_upload_service import process_company_file_upload
from schemas.jobseeker_schemas.seeker_file_upload_schemas import FileUploadResponse
from schemas.company_schemas.company_file_upload_schemas import JDUploadResponse, CompanyIntroUploadResponse

upload_router = APIRouter(prefix="/upload", tags=["File Upload"])

@upload_router.post("/jobseeker-docs", response_model=FileUploadResponse)
async def upload_jobseeker_docs(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    file_type: str = Form("portfolio"),
    db: Session = Depends(get_db)
):
    """
    구직자 문서 업로드 (이력서 또는 포트폴리오)
    
    Parameters:
    - **file**: 업로드 파일
    - **jobseeker_id**: 구직자 ID (PK)
    - **file_type**: "resume" 또는 "portfolio"
    
    Returns:
    - file_id: 파일 고유 ID
    - ncs_level: 파싱된 NCS 레벨
    - rcs_level: 파싱된 RCS 레벨
    - parsed_markdown: 전체 마크다운 내용
    - created_at: 생성 시간
    """
    if file_type not in ["resume", "portfolio"]:
        raise HTTPException(
            status_code=400,
            detail="file_type은 'resume' 또는 'portfolio' 중 하나여야 합니다."
        )
    
    # DB에서 사용자 조회 (ID 기준)
    jobseeker = db.query(Jobseeker).filter(Jobseeker.id == user_id).first()
    
    if not jobseeker:
        raise HTTPException(
            status_code=404,
            detail=f"해당 ID({user_id})를 가진 구직자를 찾을 수 없습니다."
        )
    
    user_id = jobseeker.id
    
    # 세션 ID 생성 (기존 서비스가 요구)
    session_id = str(uuid4())
    
    return await process_file_upload(
        session_id=session_id,
        file_type=file_type,
        file=file,
        user_id=user_id,
        db=db
    )


@upload_router.post("/company-docs", response_model=Union[JDUploadResponse, CompanyIntroUploadResponse])
async def upload_company_docs(
    file: UploadFile = File(...),
    company_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """
    기업 문서 업로드 (자동 분류)
    - 기업 소개서(Company Intro) 또는 채용 공고(Recruitment Notice)를 자동으로 분류하여 처리합니다.
    - 채용 공고의 경우, 직군(Job Group)을 자동 추출하여 저장합니다.
    
    Parameters:
    - **file**: 업로드 파일 (PDF, DOCX 등)
    - **company_id**: 기업 ID (DB PK)
    
    Returns:
    - JDUploadResponse 또는 CompanyIntroUploadResponse
    """
    
    # 세션 ID 생성 (기존 서비스가 요구)
    session_id = str(uuid4())
    
    return await process_company_file_upload(
        session_id=session_id,
        file_type="company_docs",
        file=file,
        user_id=company_id,
        db=db
    )


