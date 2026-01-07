from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from src.api.deps import get_db
from src.services.recommendation_service import RecommendationService
from src.schemas.recommendation_schemas import (
    JobseekerRecommendationResponse, 
    CompanyRecommendationResponse, 
    InterviewInviteRequest
)

recommendation_router = APIRouter()
service = RecommendationService()

@recommendation_router.get("/recommendations/jobseeker/{jobseeker_id}", response_model=List[JobseekerRecommendationResponse])
def get_jobseeker_recommendations(jobseeker_id: int, db: Session = Depends(get_db)):
    """
    구직자용 추천 기업 목록 조회
    """
    return service.get_jobseeker_recommendations(db, jobseeker_id)

@recommendation_router.get("/recommendations/company/{company_id}", response_model=List[CompanyRecommendationResponse])
def get_company_recommendations(company_id: int, db: Session = Depends(get_db)):
    """
    기업용 추천 구직자 목록 조회
    """
    return service.get_company_recommendations(db, company_id)

@recommendation_router.post("/interview/invite")
def send_interview_invite(request: InterviewInviteRequest, db: Session = Depends(get_db)):
    """
    면접 요청 보내기 (이메일 발송 시뮬레이션)
    """
    try:
        service.send_interview_invite(db, request.jobseeker_id)
        return {"message": "Interview invitation sent successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
