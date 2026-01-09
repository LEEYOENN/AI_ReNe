from sqlalchemy.orm import Session
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from src.models.interview import CompanyAIInterview
from src.models.user import Jobseeker
from src.models.user import JobGroup
from src.models.user import Company
from datetime import datetime

class CompanyAIInterviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, interview_data: dict):
        """
        딕셔너리 데이터를 받아서 CompanyAIInterview 엔티티를 생성하고 저장
        """
        try:
            # 데이터 매핑 로직
            interview = CompanyAIInterview(
                jobseeker_id=interview_data["jobseeker_id"],
                job_group_id=interview_data["job_group_id"],
                session_id=interview_data["session_id"],
                full_transcript=interview_data["full_transcript"],
                report=interview_data["report"],
                summary=interview_data["summary"],
                total_score=interview_data["total_score"],
                skills_evaluation=interview_data["skills_evaluation"], # JSON/List 그대로 들어감
                ai_result=interview_data["ai_result"],
                best_answer=interview_data["best_answer"],
                worst_answer=interview_data["worst_answer"],
                total_advice=interview_data["total_advice"],
                better_answer_list=interview_data["better_answer_list"],
                end_time=datetime.now()
            )
            self.db.add(interview)
            self.db.commit()
            self.db.refresh(interview)
            return interview
        except Exception as e:
            self.db.rollback()
            raise e
        
    def get_by_id(self, interview_id: int):
        return (
            self.db.query(CompanyAIInterview)
            .filter(CompanyAIInterview.id == interview_id)
            .order_by(CompanyAIInterview.created_at.desc())
            .first()
        )
    
    def get_with_details_by_id(self, interview_id: int):
        """
        인터뷰 정보와 함께 구직자명, 기업명, 직군명을 조인하여 가져옵니다.
        """
        return (
            self.db.query(
                CompanyAIInterview,
                Jobseeker.name.label("jobseeker_name"),
                Company.name.label("company_name"),
                JobGroup.name.label("job_group_name"),
                Jobseeker.email.label("jobseeker_email"),
            )
            # Innter Join 수행
            .join(Jobseeker, CompanyAIInterview.jobseeker_id == Jobseeker.id)
            .join(JobGroup, CompanyAIInterview.job_group_id == JobGroup.id)
            .join(Company, JobGroup.company_id == Company.id)
            .filter(CompanyAIInterview.id == interview_id)
            .first()
        )
    
    def get_by_job_group_id_for_dashboard(self, job_group_id: int):
        """기업 대시보드에 보여줄 구직자들이 본 면접 리스트를 가져옵니다."""
        return (
            self.db.query(
                CompanyAIInterview,
                Jobseeker.name.label("jobseeker_name"),
                Jobseeker.email.label("jobseeker_email"),
            )
            .join(Jobseeker, CompanyAIInterview.jobseeker_id == Jobseeker.id)
            .filter(CompanyAIInterview.job_group_id == job_group_id)
            .order_by(CompanyAIInterview.created_at.desc())
            .all()
        )