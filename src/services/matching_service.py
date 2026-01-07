from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from langchain_chroma import Chroma
from core.vector_store import get_vector_store
from models.document import RecruitmentNotice, Resume, Portfolio
from models.user import Jobseeker
from models.vector_mapping import RecruitmentNoticeVectorMapping, JobseekerVectorMapping

class MatchingService:
    def __init__(self, db: Session):
        self.db = db
        self.jobseeker_collection_name = "jobseeker_docs" 
        self.company_collection_name = "company_jds"
        self.jobseeker_vector_store = get_vector_store(self.jobseeker_collection_name)
        self.company_vector_store = get_vector_store(self.company_collection_name)

    def find_top_candidates(self, recruitment_notice_id: int, top_k: int = 10) -> List[Dict]:
        """
        Find top K candidates for a given recruitment notice using vector similarity.
        """
        # 1. Get Recruitment Notice
        notice = self.db.query(RecruitmentNotice).filter(RecruitmentNotice.id == recruitment_notice_id).first()
        if not notice:
            raise ValueError(f"Recruitment Notice {recruitment_notice_id} not found")

        # 2. Perform Vector Search
        results = self.jobseeker_vector_store.similarity_search_with_score(
            query=notice.markdown_content,
            k=top_k
        )
        
        candidates = []
        for doc, score in results:
            # Metadata contains user_id (which is jobseeker_id)
            jobseeker_id = doc.metadata.get("user_id")
            if jobseeker_id:
                candidates.append({
                    "jobseeker_id": int(jobseeker_id),
                    "score": score, 
                    "content": doc.page_content
                })
                
        return candidates

    def find_top_notices(self, jobseeker_id: int, top_k: int = 10) -> List[Dict]:
        """
        Find top K recruitment notices for a given jobseeker using vector similarity.
        """
        # 1. Get Jobseeker's Resume
        resume = self.db.query(Resume).filter(Resume.jobseeker_id == jobseeker_id).order_by(Resume.id.desc()).first()
        if not resume:
            raise ValueError(f"Resume for Jobseeker {jobseeker_id} not found")

        # 2. Perform Vector Search
        results = self.company_vector_store.similarity_search_with_score(
            query=resume.markdown_content,
            k=top_k
        )
        
        notices = []
        for doc, score in results:
            # Metadata contains db_record_id (which is recruitment_notice_id)
            notice_id = doc.metadata.get("db_record_id")
            company_id = doc.metadata.get("user_id")
            if notice_id:
                notices.append({
                    "recruitment_notice_id": int(notice_id),
                    "company_id": int(company_id) if company_id else None,
                    "score": score,
                    "content": doc.page_content
                })
                
        return notices

    def filter_candidates_by_skills(self, candidates: List[Dict], required_skills: List[str]) -> List[Dict]:
        """
        Filter candidates who do not possess required skills.
        This is a placeholder for Q2 requirement.
        """
        filtered = []
        for cand in candidates:
            # Logic to check skills from candidate profile/resume
            # For now, we pass everyone as we don't have structured skill data easily accessible here without DB query
            # In a real impl, we would query Resume.skills
            filtered.append(cand)
        return filtered
