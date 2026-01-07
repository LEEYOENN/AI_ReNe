import os, sys
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from core.database import Base


class JobseekerVectorMapping(Base):
    __tablename__ = "jobseeker_vector_mapping"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jobseeker_id = Column(Integer, ForeignKey("jobseeker.id", ondelete="CASCADE"), nullable=False)
    collection_name = Column(String(255), nullable=False)
    collection_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    jobseeker = relationship("Jobseeker", back_populates="vector_mappings")

class CompanyVectorMapping(Base):
    __tablename__ = "company_vector_mapping"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    collection_name = Column(String(255), nullable=False)
    collection_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
        
    # 외래키: jobseeker에서 company_vector_mapping를 부를 때 'company_vector_mappings'라고 부르다
    company = relationship("Company", back_populates="vector_mappings")

class JobGroupVectorMapping(Base):
    __tablename__ = "job_group_vector_mapping"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_group_id = Column(Integer, ForeignKey("job_group.id", ondelete="CASCADE"), nullable=False)
    collection_name = Column(String(255), nullable=False)
    collection_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    job_group = relationship("JobGroup", back_populates="vector_mappings")

class RecruitmentNoticeVectorMapping(Base):
    __tablename__ = "recruitment_notice_vector_mapping"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    recruitment_notice_id = Column(Integer, ForeignKey("recruitment_notice.id", ondelete="CASCADE"), nullable=False)
    collection_name = Column(String(255), nullable=False)
    collection_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    recruitment_notice = relationship("RecruitmentNotice", back_populates="vector_mappings")



