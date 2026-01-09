import os, sys
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    JSON,
    func,
    Text,
    Boolean,
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import relationship
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from core.database import Base


# 1. 르네 인터뷰 (SuperType)
class ReneInterview(Base):
    __tablename__ = "rene_interview"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    jobseeker_id = Column(
        Integer, ForeignKey("jobseeker.id", ondelete="CASCADE"), nullable=False
    )  # 외래키
    interview_type = Column(String(50), nullable=False) # Beginning, Growth, Trials
    full_transcript = Column(LONGTEXT, nullable=True)
    report = Column(LONGTEXT, nullable=False) # 사용자에게 보여줄 면접 보고서
    summary = Column(Text, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    jobseeker = relationship("Jobseeker", back_populates="rene_interviews")

    # 1:1 매핑 관계 설정 (uselist=False)
    beginning_rene_detail = relationship(
        "BeginningReneDetail",
        back_populates="rene_interview",
        uselist=False,
        cascade="all, delete-orphan",
    )
    growth_rene_detail = relationship(
        "GrowthReneDetail",
        back_populates="rene_interview",
        uselist=False,
        cascade="all, delete-orphan",
    )
    trials_rene_detail = relationship(
        "TrialsReneDetail",
        back_populates="rene_interview",
        uselist=False,
        cascade="all, delete-orphan",
    )


# 2. 시작의 르네 인터뷰 (SubType)
class BeginningReneDetail(Base):
    __tablename__ = "beginning_rene_detail"

    # 1:1 식별관계
    id = Column(
        Integer, ForeignKey("rene_interview.id", ondelete="CASCADE"), primary_key=True
    )
    occupational_skills = Column(JSON, nullable=False) # 활용 직업 기술
    recommended_jobs = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    rene_interview = relationship(
        "ReneInterview", back_populates="beginning_rene_detail"
    )


# 3. 성장의 르네 인터뷰 (SubType)
class GrowthReneDetail(Base):
    __tablename__ = "growth_rene_detail"

    id = Column(
        Integer, ForeignKey("rene_interview.id", ondelete="CASCADE"), primary_key=True
    )
    total_score = Column(Float, nullable=False)
    skills_evaluation = Column(JSON, nullable=True) # 면접자가 말했던 기술들에 대한 레벨을 평가한 JSON
    ai_result = Column(String(20), nullable=False)  # PASS, FAIL, HOLD
    best_answer = Column(Text, nullable=False)
    worst_answer = Column(Text, nullable=False)
    total_advice = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    rene_interview = relationship("ReneInterview", back_populates="growth_rene_detail")


# 4. 시련의 르네 인터뷰 (SubType)
class TrialsReneDetail(Base):
    __tablename__ = "trials_rene_detail"

    id = Column(
        Integer, ForeignKey("rene_interview.id", ondelete="CASCADE"), primary_key=True
    )
    total_score = Column(Float, nullable=False)
    skills_evaluation = Column(JSON, nullable=True) # 면접자가 말했던 기술들에 대한 레벨을 평가한 JSON
    ai_result = Column(String(20), nullable=False)  # PASS, FAIL, HOLD
    best_answer = Column(Text, nullable=False)
    worst_answer = Column(Text, nullable=False)
    total_advice = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    rene_interview = relationship("ReneInterview", back_populates="trials_rene_detail")

# class ReneInterviewSession(Base):
#     __tablename__ = "rene_interview_session"

#     # UUID를 사용하여 예측 불가능한 세션 ID 생성 (보안상 추천)
#     session_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
#     # 어떤 구직자의 면접인가?
#     jobseeker_id = Column(Integer, ForeignKey("jobseeker.id", ondelete="CASCADE"), nullable=False)
    
#     # 어떤 직군에 대한 면접인가? (질문 생성을 위해 필요)
#     job_group_id = Column(Integer, ForeignKey("job_group.id", ondelete="CASCADE"), nullable=False)

#     # --- 진행 상태 관리 ---
#     status = Column(String(20), default="IN_PROGRESS") # 진행중, 완료, 에러 등
#     current_turn = Column(Integer, default=0) # 현재 턴 수 (예: 5/10)
#     interview_stage = Column(String(50), default="INTRO") # 현재 단계 (자기소개, 기술면접 등)
    
#     # --- 대화 기록 (LangGraph Memory 역할) ---
#     # 방법 1: JSON으로 통째로 저장 (간편함, MySQL/Postgres 지원)
#     # 대화 내용: [{"role": "ai", "content": "..."}, {"role": "user", "content": "..."}]
#     chat_history = Column(JSON, nullable=True) 

#     # --- 메타 데이터 ---
#     created_at = Column(DateTime, server_default=func.now(), nullable=False)
#     updated_at = Column(DateTime, onupdate=func.now())

#     # 관계 설정
#     jobseeker = relationship("Jobseeker")
#     # 나중에 결과 테이블과 1:1로 매핑될 수 있음
#     result = relationship("CompanyAIInterview", back_populates="session", uselist=False)


# 5. 기업 AI 면접
class CompanyAIInterview(Base):
    __tablename__ = "company_ai_interview"

    id = Column(Integer, primary_key=True, index=True)
    jobseeker_id = Column(
        Integer, ForeignKey("jobseeker.id", ondelete="CASCADE"), nullable=False
    )
    job_group_id = Column(
        Integer, ForeignKey("job_group.id", ondelete="CASCADE"), nullable=False
    )
    session_id = Column(
        String(255), ForeignKey("company_ai_interview_session.session_id"), nullable=False
    )
    full_transcript = Column(LONGTEXT, nullable=True)
    report = Column(LONGTEXT, nullable=False)
    summary = Column(Text, nullable=False)
    total_score = Column(Float, nullable=False)
    skills_evaluation = Column(JSON, nullable=True) # 면접자가 말했던 기술들에 대한 레벨을 평가한 JSON
    ai_result = Column(String(20), nullable=False)
    best_answer = Column(Text, nullable=False)
    worst_answer = Column(Text, nullable=False)
    total_advice = Column(Text, nullable=False)
    # [NEW] 모범 답안 리스트 저장용 JSON 컬럼
    better_answer_list = Column(JSON, nullable=True)
    end_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    jobseeker = relationship("Jobseeker", back_populates="company_ai_interviews")
    job_group = relationship("JobGroup", back_populates="company_ai_interviews")
    session = relationship("CompanyAIInterviewSession", back_populates="result")

class CompanyAIInterviewSession(Base):
    __tablename__ = "company_ai_interview_session"

    # UUID를 사용하여 예측 불가능한 세션 ID 생성 (보안상 추천)
    session_id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 어떤 구직자의 면접인가?
    jobseeker_id = Column(Integer, ForeignKey("jobseeker.id", ondelete="CASCADE"), nullable=False)
    
    # 어떤 직군에 대한 면접인가? (질문 생성을 위해 필요)
    job_group_id = Column(Integer, ForeignKey("job_group.id", ondelete="CASCADE"), nullable=False)

    # --- 진행 상태 관리 ---
    status = Column(String(20), default="IN_PROGRESS") # 진행중, 완료, 에러 등
    current_turn = Column(Integer, default=0) # 현재 턴 수 (예: 5/10)
    interview_stage = Column(String(50), default="INTRO") # 현재 단계 (자기소개, 기술면접 등)
    
    # --- 대화 기록 (LangGraph Memory 역할) ---
    # 방법 1: JSON으로 통째로 저장 (간편함, MySQL/Postgres 지원)
    # 대화 내용: [{"role": "ai", "content": "..."}, {"role": "user", "content": "..."}]
    chat_history = Column(JSON, nullable=True) 

    # --- 메타 데이터 ---
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, onupdate=func.now())

    # 관계 설정
    jobseeker = relationship("Jobseeker")
    # 나중에 결과 테이블과 1:1로 매핑될 수 있음
    result = relationship("CompanyAIInterview", back_populates="session", uselist=False)

# 6. 비대면 화상 면접
class NonContactInterview(Base):
    __tablename__ = "non_contact_interview"

    id = Column(Integer, primary_key=True, index=True)
    jobseeker_id = Column(
        Integer, ForeignKey("jobseeker.id", ondelete="CASCADE"), nullable=False
    )
    job_group_id = Column(
        Integer, ForeignKey("job_group.id", ondelete="CASCADE"), nullable=False
    )
    start_time = Column(DateTime, nullable=False)
    is_end = Column(Boolean, default=False, nullable=False)
    report = Column(LONGTEXT, nullable=True)
    summary = Column(Text, nullable=True)
    total_score = Column(Float, nullable=True)
    skills_evaluation = Column(JSON, nullable=True) # 면접자가 말했던 기술들에 대한 레벨을 평가한 JSON
    best_answer = Column(Text, nullable=True)
    worst_answer = Column(Text, nullable=True)
    total_advice = Column(Text, nullable=True)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    jobseeker = relationship("Jobseeker", back_populates="non_contact_interviews")
    job_group = relationship("JobGroup", back_populates="non_contact_interviews")


# 7. 면접 세션 (진행 상태 관리)
class InterviewSession(Base):
    """
    면접 진행 중 상태를 저장하는 테이블.
    면접이 종료되면 이 데이터를 가공하여 위 'ReNeInterview' 등의 결과 테이블로 이관합니다.
    """
    __tablename__ = "interview_sessions"

    session_id = Column(String(50), primary_key=True)  # UUID
    user_id = Column(Integer, index=True)  # jobseeker_id와 매핑

    stage = Column(String(20))  # BEGINNING, GROWTH, TRIALS, COMPANY_AI, NON_CONTACT
    current_mode = Column(
        String(10), default="MID"
    )  # LOW, MID, HIGH (엘리베이터 알고리즘)
    turn_count = Column(Integer, default=0)  # 현재 턴 수 (최대 10회 제한용)

    # 평가 데이터 (실시간 업데이트)
    current_rcs_level = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # 1:N 관계 (대화 로그)
    logs = relationship(
        "ChatLog", back_populates="session", cascade="all, delete-orphan"
    )


# 8. 대화 로그 (컨테스트 관리)
class ChatLog(Base):
    """
    각 턴(Turn)별 대화 내용과 평가 결과를 저장하는 테이블.
    최근 2개의 대화를 불러와 LLM Context에 주입하는 용도로 사용합니다.
    """

    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), ForeignKey("interview_sessions.session_id"))
    turn_number = Column(Integer)

    user_text = Column(Text)  # STT 결과
    ai_text = Column(Text)  # 생성된 답변

    # 그 턴의 평가 결과 (Evaluator Output)
    eval_score = Column(Integer)
    eval_action = Column(String(20))  # LEVEL_UP, STAY, LEVEL_DOWN

    created_at = Column(DateTime, server_default=func.now())

    session = relationship("InterviewSession", back_populates="logs")
