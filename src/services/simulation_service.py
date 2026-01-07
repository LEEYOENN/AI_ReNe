import json
from typing import List, Dict
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

from models.user import Jobseeker, Company
from models.document import Resume, RecruitmentNotice, CompanyIntroduction
from prompts.simulation_prompts import INTERVIEWER_SYSTEM_PROMPT_TEMPLATE, CANDIDATE_SYSTEM_PROMPT_TEMPLATE
from core.config import settings

class SimulationService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = ChatOpenAI(
            model="gpt-4o-mini", 
            temperature=0.7,
            api_key=settings.OPENAI_API_KEY
        ) # Use a capable model

    def _get_jobseeker_context(self, jobseeker_id: int) -> str:
        jobseeker = self.db.query(Jobseeker).filter(Jobseeker.id == jobseeker_id).first()
        resume = self.db.query(Resume).filter(Resume.jobseeker_id == jobseeker_id).order_by(Resume.id.desc()).first()
        
        if not jobseeker or not resume:
            raise ValueError(f"Jobseeker {jobseeker_id} or Resume not found")
            
        return CANDIDATE_SYSTEM_PROMPT_TEMPLATE.format(
            candidate_name=jobseeker.name,
            resume_content=resume.markdown_content
        )

    def _get_interviewer_context(self, recruitment_notice_id: int) -> str:
        notice = self.db.query(RecruitmentNotice).filter(RecruitmentNotice.id == recruitment_notice_id).first()
        if not notice:
            raise ValueError(f"Recruitment Notice {recruitment_notice_id} not found")
            
        # Get Company Info via JobGroup -> Company
        # Assuming RecruitmentNotice -> JobGroup -> Company relationship exists
        # Based on models/document.py: RecruitmentNotice -> JobGroup
        # Based on models/user.py: JobGroup -> Company (implied, let's check if we need to join)
        
        # Let's try to access company via relationships if they are set up correctly.
        # If not, we might need to query manually.
        # RecruitmentNotice.job_group is a relationship.
        # JobGroup.company is a relationship.
        
        job_group = notice.job_group
        company = job_group.company
        
        # Try to get Company Introduction
        company_intro = self.db.query(CompanyIntroduction).filter(CompanyIntroduction.company_id == company.id).first()
        company_desc = company_intro.markdown_content if company_intro else "A innovative tech company."

        return INTERVIEWER_SYSTEM_PROMPT_TEMPLATE.format(
            company_name=company.name,
            job_title=job_group.name, # Assuming JobGroup has a name or similar field
            company_description=company_desc,
            jd_requirements=notice.markdown_content
        )

    def run_simulation(self, jobseeker_id: int, recruitment_notice_id: int) -> str:
        """
        Runs the AI2AI interview simulation.
        Returns the full transcript.
        """
        candidate_system_prompt = self._get_jobseeker_context(jobseeker_id)
        interviewer_system_prompt = self._get_interviewer_context(recruitment_notice_id)

        transcript = []
        
        # Initialize Chat Histories
        interviewer_history = [SystemMessage(content=interviewer_system_prompt)]
        candidate_history = [SystemMessage(content=candidate_system_prompt)]

        # Simulation Loop: 6 Main Questions
        for q_idx in range(1, 7):
            # 1. Interviewer asks Main Question
            if q_idx == 1:
                instruction = "Start the interview by asking the candidate to introduce themselves briefly."
            else:
                instruction = f"Ask question #{q_idx} related to the JD requirements. Do not repeat previous questions."
            
            interviewer_history.append(HumanMessage(content=instruction))
            question_msg = self.llm.invoke(interviewer_history)
            interviewer_history.append(AIMessage(content=question_msg.content)) # Add own output to history
            
            # Add to Transcript
            transcript.append(f"Interviewer: {question_msg.content}")
            
            # 2. Candidate Answers
            candidate_history.append(HumanMessage(content=question_msg.content))
            answer_msg = self.llm.invoke(candidate_history)
            candidate_history.append(AIMessage(content=answer_msg.content))
            
            # Add to Transcript
            transcript.append(f"Candidate: {answer_msg.content}")
            
            # 3. Follow-up Loop (Max 2)
            # We ask the Interviewer LLM if it wants to ask a follow-up
            # To do this effectively, we can just prompt it.
            
            for f_idx in range(2):
                # Ask Interviewer if they want to dig deeper
                decision_prompt = "Based on the candidate's answer, if it was vague or needs more technical detail, ask a follow-up question. Otherwise, say 'NEXT_TOPIC'."
                interviewer_history.append(HumanMessage(content=decision_prompt))
                follow_up_msg = self.llm.invoke(interviewer_history)
                
                if "NEXT_TOPIC" in follow_up_msg.content:
                    # Remove the decision prompt and "NEXT_TOPIC" response from history to keep it clean? 
                    # Or just keep it. Let's keep it simple.
                    interviewer_history.append(AIMessage(content=follow_up_msg.content))
                    break
                
                # It's a follow-up question
                interviewer_history.append(AIMessage(content=follow_up_msg.content))
                transcript.append(f"Interviewer (Follow-up): {follow_up_msg.content}")
                
                # Candidate Answers Follow-up
                candidate_history.append(HumanMessage(content=follow_up_msg.content))
                f_answer_msg = self.llm.invoke(candidate_history)
                candidate_history.append(AIMessage(content=f_answer_msg.content))
                transcript.append(f"Candidate: {f_answer_msg.content}")

        return "\n\n".join(transcript)
