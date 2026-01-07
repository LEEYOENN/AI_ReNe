import os, sys
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from core.database import Base

class Resume(Base):
    __tablename__ = "resume"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker.id", ondelete="CASCADE"), nullable=False)
    brief_self_introduction = Column(LONGTEXT, nullable=False)
    work_experience = Column(JSON, nullable=True)
    brief_project_introduction = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    skills = Column(JSON, nullable=True)
    certifications = Column(JSON, nullable=True)
    other_experience = Column(JSON, nullable=True)
    languages = Column(JSON, nullable=True)
    ncs_level = Column(Integer, nullable=True, comment="NCS 수준 (1~8)") # 1~8 단계
    rcs_level = Column(Integer, nullable=True, comment="RCS 수준 (1~8)") # 1~8 단계
    markdown_content = Column(LONGTEXT, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # 외래키: jobseeker에서 resume를 부를 때 'resumes'라고 부르다
    jobseeker = relationship("Jobseeker", back_populates="resumes")
    
class Portfolio(Base):
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker.id", ondelete="CASCADE"), nullable=False)
    main_skills = Column(JSON, nullable=True)
    project_details = Column(JSON, nullable=False) # 최신 5개
    ncs_level = Column(Integer, nullable=True) # NCS 수준체계 1~8 단계
    rcs_level = Column(Integer, nullable=True) # RCS 수준체계 1~8 단계
    markdown_content = Column(LONGTEXT, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    jobseeker = relationship("Jobseeker", back_populates="portfolios")

class CompanyIntroduction(Base):
    __tablename__ = "company_introduction"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    markdown_content = Column(LONGTEXT, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    company = relationship("Company", back_populates="company_introductions")


class RecruitmentNotice(Base):
    __tablename__ = "recruitment_notice"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_group_id = Column(Integer, ForeignKey("job_group.id", ondelete="CASCADE"), nullable=False)
    markdown_content = Column(LONGTEXT, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    job_group = relationship("JobGroup", back_populates="recruitment_notices")
    vector_mappings = relationship("RecruitmentNoticeVectorMapping", back_populates="recruitment_notice", cascade="all, delete-orphan")





