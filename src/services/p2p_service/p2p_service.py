from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
import os, sys

# 프로젝트 루트 경로를 sys.path에 추가 (src 상위 폴더)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.services.stt_service.faster_whisper_service import FasterWhisperService
from src.models.interview import InterviewSession, ChatLog, ReneInterview, NonContactInterview
from src.models.user import Jobseeker, JobGroup
from src.models.document import Resume, Portfolio
from src.core.database import SessionLocal
from src.agents.p2p_auditor_agent import analyze_interview_transcript
from src.schemas.p2p_schemas.p2p_response_dto import P2PChunkResponseDto, P2PReportResponseDto, P2PInterviewResultResponse
from src.services.p2p_service.buffer_manager import buffer_manager
from src.utils.audio_file_utils import pcm_to_wav_bytes
from src.utils.pdf_utils import generate_pdf_from_markdown
from datetime import datetime
import json


# Initialize STT Service
try:
    stt_service = FasterWhisperService()
except Exception as e:
    print(f"STT Service Initialization Failed: {e}")
    stt_service = None

# 단일 세션용 상수 ID
DEFAULT_SESSION_ID = "single_session_v1"

async def process_p2p_audio_chunk(
    audio_file: UploadFile, 
    speaker_role: str,
    username: str = None
) -> P2PChunkResponseDto:
    """
    [P2P] 오디오 청크를 받아 동적 버퍼링 및 STT 처리
    Args:
        username: 파일명에서 추출한 사용자 식별자 (예: jobplz)
    """
    session_id = DEFAULT_SESSION_ID
    
    # Username이 전달되면 BufferManager에 저장 (세션별 사용자 매핑)
    if username:
        buffer_manager.set_session_user(session_id, username)
    
    if not stt_service:
        raise HTTPException(status_code=500, detail="STT Service is not available")

    # Step A: 현재 버퍼 상태 확인 (마지막 화자)
    last_speaker = buffer_manager.get_last_speaker(session_id)
    
    # 오디오 데이터 읽기 (PCM)
    audio_bytes = await audio_file.read()
    
    # Step B: 화자가 동일하면 버퍼링 (STT 수행 X)
    if last_speaker == speaker_role:
        buffer_manager.append_audio(session_id, audio_bytes)
        return P2PChunkResponseDto(
            session_id=session_id,
            turn_number=0, # DB 제거로 인해 턴 카운트 추적 생략 (필요시 파일 기반 구현 가능)
            text="", # 버퍼링 중이므로 텍스트 없음
            status="buffered"
        )
    
    # Step C: 화자가 바뀌면 플러시 & 변환
    # 1. 이전 화자의 오디오 버퍼 처리
    if last_speaker is not None:
        buffered_audio = buffer_manager.read_and_clear_buffer(session_id)
        if buffered_audio:
            # PCM -> WAV 변환
            wav_bytes = pcm_to_wav_bytes(buffered_audio)
            transcribed_text = stt_service.transcribe(wav_bytes)
            if transcribed_text:
                buffer_manager.save_transcript(session_id, last_speaker, transcribed_text)
    
    # 2. 현재 화자의 오디오로 새 버퍼 시작
    buffer_manager.append_audio(session_id, audio_bytes)
    buffer_manager.update_last_speaker(session_id, speaker_role)
    
    return P2PChunkResponseDto(
        session_id=session_id,
        turn_number=0,
        text="", # 현재 청크는 버퍼링 시작됨
        status="buffered"
    )

async def finalize_p2p_interview() -> int:
    """
    [P2P] 인터뷰 종료 및 보고서 생성 (DB 저장)
    Returns:
        int: 생성된 NonContactInterview ID
    """
    session_id = DEFAULT_SESSION_ID
    
    # 0. 남은 버퍼 강제 플러시 (Flush remaining buffer)
    last_speaker = buffer_manager.get_last_speaker(session_id)
    if last_speaker:
        buffered_audio = buffer_manager.read_and_clear_buffer(session_id)
        if buffered_audio:
            wav_bytes = pcm_to_wav_bytes(buffered_audio)
            transcribed_text = stt_service.transcribe(wav_bytes)
            if transcribed_text:
                buffer_manager.save_transcript(session_id, last_speaker, transcribed_text)

    # 1. 구직자 프로필 구성 (DB 연동)
    session_username = buffer_manager.get_session_user(session_id)
    
    candidate_profile = {
        "user_id": "Unknown",
        "name": "Unknown",
        "skills": [],
        "portfolio_markdown": "" 
    }
    
    db = SessionLocal()
    try:
        jobseeker = None
        if session_username:
            jobseeker = db.query(Jobseeker).filter(Jobseeker.email == session_username).first()
            if not jobseeker:
                print(f"[P2P Service] 해당 이메일의 구직자를 찾을 수 없습니다: {session_username}")
        else:
            target_jobseeker_id = 2
            jobseeker = db.query(Jobseeker).filter(Jobseeker.id == target_jobseeker_id).first()
            print(f"[P2P Service] 세션 유저 정보가 없어 기본 ID({target_jobseeker_id})로 조회합니다.")

        if jobseeker:
            candidate_profile["user_id"] = str(jobseeker.id)
            candidate_profile["name"] = jobseeker.name
            
            portfolio = db.query(Portfolio).filter(Portfolio.jobseeker_id == jobseeker.id).order_by(Portfolio.created_at.desc()).first()
            resume = db.query(Resume).filter(Resume.jobseeker_id == jobseeker.id).order_by(Resume.created_at.desc()).first()
            
            summary_parts = []
            
            skills_list = []
            if portfolio and portfolio.main_skills:
                skills_list = portfolio.main_skills
            elif resume and resume.skills:
                skills_list = resume.skills
                
            if skills_list:
                normalized_skills = []
                for s in skills_list:
                    if isinstance(s, str):
                        normalized_skills.append(s)
                    elif isinstance(s, dict):
                        normalized_skills.append(s.get("tech_keyword") or s.get("name") or str(s))
                
                summary_parts.append(f"# [Skills]\n- {', '.join(normalized_skills)}")
                
                for s in normalized_skills:
                    candidate_profile["skills"].append({
                        "tech_keyword": s,
                        "current_level": 1,
                        "context": ""
                    })

            if portfolio and portfolio.project_details:
                projects_str = ["# [Key Projects]"]
                for idx, proj in enumerate(portfolio.project_details, 1):
                    if isinstance(proj, dict):
                        name = proj.get("project_name", "Unknown Project")
                        role = proj.get("position", "")
                        desc = proj.get("description", "")
                        projects_str.append(f"{idx}. {name} ({role})\n   - {desc}")
                if len(projects_str) > 1:
                    summary_parts.append("\n".join(projects_str))

            if resume and resume.work_experience:
                exp_str = ["# [Experience]"]
                for idx, exp in enumerate(resume.work_experience, 1):
                    if isinstance(exp, dict):
                        company = exp.get("company_name", "Unknown Company")
                        role = exp.get("role", "")
                        period = exp.get("period", "")
                        exp_str.append(f"{idx}. {company} ({role}) | {period}")
                if len(exp_str) > 1:
                    summary_parts.append("\n".join(exp_str))
            
            if resume and resume.education:
                edu_str = ["# [Education]"]
                for edu in resume.education:
                    edu_str.append(f"- {edu}")
                if len(edu_str) > 1:
                    summary_parts.append("\n".join(edu_str))

            if summary_parts:
                candidate_profile["portfolio_summary"] = "\n\n".join(summary_parts)
            elif portfolio and portfolio.markdown_content:
                candidate_profile["portfolio_summary"] = portfolio.markdown_content
            else:
                candidate_profile["portfolio_summary"] = "No portfolio data available."

        else:
            print(f"[P2P Service] 구직자를 찾을 수 없습니다.")
            
        # Fallback for portfolio summary
        if not candidate_profile.get("portfolio_summary"):
            candidate_profile["portfolio_summary"] = """
# [Basic Information]
- **Name:** Unknown
- **Summary:** No portfolio data available.
"""
            candidate_profile["skills"] = []

        # 2. 전체 대화록 구성
        full_transcript = buffer_manager.get_full_transcript(session_id)

        # 3. P2P Auditor Agent 호출
        try:
            analysis_result = analyze_interview_transcript(candidate_profile, full_transcript)
        except Exception as e:
            print(f"Agent Analysis Failed: {e}")
            raise HTTPException(status_code=500, detail=f"Report generation failed: {e}")

        # 4. 결과 저장 (DB)
        update_data = analysis_result.get("update_data", {})
        human_report = analysis_result.get("human_report", "")
        
        # Job Group 조회 (Fallback)
        job_group = db.query(JobGroup).first()
        job_group_id = job_group.id if job_group else 1 # Default to 1 if no job group found

        # NonContactInterview 생성
        interview_result = NonContactInterview(
            jobseeker_id=int(candidate_profile["user_id"]) if candidate_profile["user_id"] != "Unknown" else 2,
            job_group_id=job_group_id,
            start_time=datetime.now(), # 임시
            end_time=datetime.now(),
            is_end=True,
            report=update_data.get("report", human_report), # JSON의 report 우선, 없으면 Markdown
            summary=update_data.get("summary", "요약 정보 없음"),
            total_score=update_data.get("total_score", 0.0),
            skills_evaluation=update_data.get("skills_evaluation", []),
            ai_result=update_data.get("ai_result", "HOLD"),
            best_answer=update_data.get("best_answer", ""),
            worst_answer=update_data.get("worst_answer", ""),
            total_advice=update_data.get("total_advice", ""),
            better_answer_list=update_data.get("better_answer_list", []),
            full_transcript=full_transcript
        )
        
        db.add(interview_result)
        db.commit()
        db.refresh(interview_result)
        
        print(f"[P2P Service] Interview Result Saved. ID: {interview_result.id}")
        
        # 세션 데이터 정리
        # buffer_manager.clear_session(session_id)

        return interview_result.id

    except Exception as e:
        db.rollback()
        print(f"[P2P Service] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save interview result: {e}")
    finally:
        db.close()

def reset_p2p_session():
    """
    [P2P] 세션 데이터 초기화 (새로운 면접 시작 전 호출)
    """
    session_id = DEFAULT_SESSION_ID
    buffer_manager.clear_session(session_id)
    print(f"[P2P Service] Session {session_id} has been reset.")