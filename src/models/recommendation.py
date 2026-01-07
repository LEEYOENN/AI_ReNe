import os, sys
from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import relationship
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from core.database import Base

class RecommendationResult(Base):
    __tablename__ = "recommendation_result"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker.id", ondelete="CASCADE"), nullable=False)
    recruitment_notice_id = Column(Integer, ForeignKey("recruitment_notice.id", ondelete="CASCADE"), nullable=False)
    
    total_score = Column(Float, nullable=False)
    score_details = Column(JSON, nullable=False, comment="{'technical': 40, 'problem_solving': 30, 'culture': 20, 'growth': 10}")
    swot_analysis = Column(JSON, nullable=False, comment="{'S': [], 'W': [], 'O': [], 'T': []}")
    summary = Column(String(1000), nullable=True, comment="Evaluation Summary")
    
    is_recommended = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    jobseeker = relationship("Jobseeker")
    recruitment_notice = relationship("RecruitmentNotice")
