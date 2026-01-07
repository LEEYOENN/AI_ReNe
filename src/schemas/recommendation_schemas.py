from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class ScoreDetails(BaseModel):
    technical: float
    problem_solving: float
    culture: float
    growth: float

class SWOTAnalysis(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    opportunities: List[str]
    threats: List[str]

class RecommendationResultBase(BaseModel):
    jobseeker_id: int
    recruitment_notice_id: int
    total_score: float
    score_details: ScoreDetails
    swot_analysis: SWOTAnalysis
    summary: Optional[str] = None
    is_recommended: bool

class RecommendationResultCreate(RecommendationResultBase):
    pass

class RecommendationResultResponse(RecommendationResultBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class JobseekerRecommendationResponse(RecommendationResultResponse):
    company_name: str
    notice_title: str

class CompanyRecommendationResponse(RecommendationResultResponse):
    jobseeker_name: str
    jobseeker_email: str

class InterviewInviteRequest(BaseModel):
    jobseeker_id: int
    recruitment_notice_id: int
