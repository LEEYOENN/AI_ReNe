import json
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from models.recommendation import RecommendationResult
from models.document import RecruitmentNotice, Resume
from prompts.recommendation_auditor_prompt import AUDITOR_SYSTEM_PROMPT, AUDITOR_USER_PROMPT_TEMPLATE
from schemas.recommendation_schemas import ScoreDetails, SWOTAnalysis
from core.config import settings

# Define Pydantic model for LLM Output Parsing
class AuditorOutput(BaseModel):
    score_details: ScoreDetails
    total_score: float
    swot_analysis: SWOTAnalysis
    consistency_check: str
    summary: str

class AuditorService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = ChatOpenAI(
            model="gpt-4o", 
            temperature=0,
            api_key=settings.OPENAI_API_KEY
        ) # Use GPT-4 for evaluation accuracy
        self.parser = JsonOutputParser(pydantic_object=AuditorOutput)

    def evaluate_and_save(self, jobseeker_id: int, recruitment_notice_id: int, transcript: str) -> RecommendationResult:
        """
        Evaluates the interview transcript and saves the result to DB.
        """
        # 1. Fetch Context
        notice = self.db.query(RecruitmentNotice).filter(RecruitmentNotice.id == recruitment_notice_id).first()
        resume = self.db.query(Resume).filter(Resume.jobseeker_id == jobseeker_id).order_by(Resume.id.desc()).first()
        
        if not notice or not resume:
            raise ValueError("Recruitment Notice or Resume not found")

        # 2. Prepare Prompt
        user_prompt = AUDITOR_USER_PROMPT_TEMPLATE.format(
            jd_content=notice.markdown_content,
            resume_summary=resume.markdown_content[:2000], # Truncate if too long
            transcript=transcript
        )

        messages = [
            SystemMessage(content=AUDITOR_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]

        # 3. Invoke LLM
        try:
            response = self.llm.invoke(messages)
            parsed_result = self.parser.parse(response.content)
        except Exception as e:
            print(f"Error during LLM evaluation: {e}")
            # Fallback or re-raise
            raise e

        # 4. Determine Recommendation (Pass/Fail)
        # Threshold: 70 points
        is_recommended = parsed_result["total_score"] >= 70.0

        # 5. Save to DB
        recommendation = RecommendationResult(
            jobseeker_id=jobseeker_id,
            recruitment_notice_id=recruitment_notice_id,
            total_score=parsed_result["total_score"],
            score_details=parsed_result["score_details"],
            swot_analysis=parsed_result["swot_analysis"],
            summary=parsed_result.get("summary", ""),
            is_recommended=is_recommended
        )
        
        self.db.add(recommendation)
        self.db.commit()
        self.db.refresh(recommendation)
        
        return recommendation
