import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from sqlalchemy.orm import Session
from src.models.recommendation import RecommendationResult
from src.models.user import Jobseeker, Company, JobGroup
from src.models.document import RecruitmentNotice
from src.schemas.recommendation_schemas import JobseekerRecommendationResponse, CompanyRecommendationResponse
import logging

logger = logging.getLogger(__name__)

class RecommendationService:
    def get_jobseeker_recommendations(self, db: Session, jobseeker_id: int):
        results = (
            db.query(RecommendationResult, Company.name, JobGroup.name)
            .join(RecruitmentNotice, RecommendationResult.recruitment_notice_id == RecruitmentNotice.id)
            .join(JobGroup, RecruitmentNotice.job_group_id == JobGroup.id)
            .join(Company, JobGroup.company_id == Company.id)
            .filter(RecommendationResult.jobseeker_id == jobseeker_id)
            .all()
        )
        
        response = []
        for rec, company_name, job_group_name in results:
            # Map to response schema
            item = JobseekerRecommendationResponse(
                id=rec.id,
                jobseeker_id=rec.jobseeker_id,
                recruitment_notice_id=rec.recruitment_notice_id,
                total_score=rec.total_score,
                score_details=rec.score_details,
                swot_analysis=rec.swot_analysis,
                summary=rec.summary,
                is_recommended=rec.is_recommended,
                created_at=rec.created_at,
                company_name=company_name,
                notice_title=job_group_name # Using JobGroup name as notice title for now
            )
            response.append(item)
        return response

    def get_company_recommendations(self, db: Session, company_id: int):
        results = (
            db.query(RecommendationResult, Jobseeker.name, Jobseeker.email)
            .join(Jobseeker, RecommendationResult.jobseeker_id == Jobseeker.id)
            .join(RecruitmentNotice, RecommendationResult.recruitment_notice_id == RecruitmentNotice.id)
            .join(JobGroup, RecruitmentNotice.job_group_id == JobGroup.id)
            .filter(JobGroup.company_id == company_id)
            .all()
        )
        
        response = []
        for rec, jobseeker_name, jobseeker_email in results:
            item = CompanyRecommendationResponse(
                id=rec.id,
                jobseeker_id=rec.jobseeker_id,
                recruitment_notice_id=rec.recruitment_notice_id,
                total_score=rec.total_score,
                score_details=rec.score_details,
                swot_analysis=rec.swot_analysis,
                summary=rec.summary,
                is_recommended=rec.is_recommended,
                created_at=rec.created_at,
                jobseeker_name=jobseeker_name,
                jobseeker_email=jobseeker_email
            )
            response.append(item)
        return response

    def send_interview_invite(self, db: Session, jobseeker_id: int):
        jobseeker = db.query(Jobseeker).filter(Jobseeker.id == jobseeker_id).first()
        if not jobseeker:
            raise ValueError("Jobseeker not found")
        
        email_content = f"""
        To: {jobseeker.email}
        Subject: 면접 초대
        
        면접 초대를 받았습니다. 초대 코드는 "4885" (하드코딩) 입니다.
        """
        logger.info(f"Sending Email:\n{email_content}")
        print(f"Sending Email:\n{email_content}") # Print to console as well for visibility
        return True
