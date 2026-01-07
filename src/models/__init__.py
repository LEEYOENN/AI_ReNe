"""DB 테이블 생성 (서비스의 객체(Entity) 정의"""
from .user import (
    Jobseeker, 
    Company, 
    JobGroup
)
from .interview import (
    CompanyAIInterview,
    CompanyAIInterviewSession, 
    NonContactInterview,
    ReneInterview,
    BeginningReneDetail,
    GrowthReneDetail,
    TrialsReneDetail,
    InterviewSession,
    ChatLog
)
from .vector_mapping import (
    JobseekerVectorMapping, 
    CompanyVectorMapping, 
    JobGroupVectorMapping
)
from .document import (
    Resume,
    Portfolio,
    CompanyIntroduction,
    RecruitmentNotice
)
from .recommendation import RecommendationResult



