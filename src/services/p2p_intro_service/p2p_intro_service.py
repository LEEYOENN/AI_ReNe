from sqlalchemy.orm import Session
import os, sys
import uuid
import base64
from datetime import datetime
from fastapi import UploadFile, HTTPException
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from src.repositories.company_ai_interview_repository.company_ai_interview_repository import CompanyAIInterviewRepository
from src.schemas.p2p_intro_schemas import p2p_intro_response_dto
# from src.
class P2PIntroService:
    def __init__(self, db: Session):
        self.db = db
        self.company_ai_interview_repo = CompanyAIInterviewRepository(db)

    def get_brief_interview_info_list(self, job_group_id: int):
        """
        특정 직군의 지원자 면접 결과 리스트를 반환합니다 (대시보드용).
        """
        # 1. Repository 호출 (작성하신 함수)
        rows = self.company_ai_interview_repo.get_by_job_group_id_for_dashboard(job_group_id)

        interview_list = []

        # 2. 결과 매핑 (Row -> DTO)
        for row in rows:
            interview = row.CompanyAIInterview
        