from sqlalchemy.orm import Session
import os, sys
import uuid
import base64
from datetime import datetime
from premailer import transform
from fastapi import UploadFile, HTTPException, BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from src.repositories.resume_repository.resume_repository import ResumeRepository
from src.repositories.portfolio_repository.portfolio_repository import PortfolioRepository
from src.repositories.company_repository.company_repository import CompanyRepository
from src.repositories.recruitment_notice_repository.recruitment_notice_repository import RecruitmentNoticeRepository
from src.repositories.company_introduction_repository.company_introduction_repository import CompanyIntroductionRepository
from src.repositories.jobseeker_repository.jobseeker_repository import JobseekerRepository
from src.repositories.company_ai_interview_repository.company_ai_interview_repository import CompanyAIInterviewRepository
from src.repositories.job_group_repository.job_group_repository import JobGroupRepository
from src.agents.company_ai_interview_graph import CompanyAIInterviewAgent
from src.services.stt_service.faster_whisper_service import stt_service
from src.services.tts_service.elevenlabs_tts_service import tts_service
from src.utils.audio_file_utils import pcm_to_wav_bytes
from src.schemas.company_ai_interview_schemas import company_ai_interview_request_dto, company_ai_interview_response_dto
from src.repositories.company_ai_interview_session_repository.company_ai_interview_session_repository import CompanyAIInterviewSessionRepository
from src.models.interview import CompanyAIInterviewSession
from src.core.config import settings

class CompanyAIInterviewService:
    def __init__(self, db: Session):
        self.db = db
        self.company_repo = CompanyRepository(db)
        self.job_group_repo = JobGroupRepository(db)
        self.jobseeker_repo = JobseekerRepository(db)
        self.resume_repo = ResumeRepository(db)
        self.portfolio_repo = PortfolioRepository(db)
        self.company_introduction_repo = CompanyIntroductionRepository(db)
        self.recruitment_notice_repo = RecruitmentNoticeRepository(db)
        self.interview_repo = CompanyAIInterviewRepository(db)
        self.session_repo = CompanyAIInterviewSessionRepository(db)
        self.agent = CompanyAIInterviewAgent()
    async def start_new_interview(self, request: company_ai_interview_request_dto.StartInterviewRequest) -> company_ai_interview_response_dto.InterviewResponse:
       
        # 1. DB에 세션 ID 생성 및 DB 레코드 선행 생성
        # angGraph에 session_id를 thread_id로 넘겨줘야 하므로, DB에 먼저 자리를 만듭니다.
        new_session_id = str(uuid.uuid4())
        new_session = CompanyAIInterviewSession(
            session_id=new_session_id,
            jobseeker_id=request.jobseeker_id,
            job_group_id=request.job_group_id,
            status="IN_PROGRESS",
            current_turn=0,
            interview_stage="INTRO",
            chat_history=[]  # 빈 리스트로 초기화
        )
        # DB에 저장 (session_id 확보)
        self.session_repo.create(new_session)

        # 2. 그래프 실행에 필요한 텍스트 데이터 조회
        
        context_data = {
            "company_name": self.company_repo.get_name(request.company_id),
            "job_group_name": self.job_group_repo.get_name_by_id(request.job_group_id),
            "jobseeker_name": self.jobseeker_repo.get_name(request.jobseeker_id),
            "company_info": self.company_repo.get_info_as_markdown(request.company_id),
            "jobseeker_info": self.jobseeker_repo.get_info_as_markdown(request.jobseeker_id),
            "resume_context": self.resume_repo.get_full_text(request.jobseeker_id),
            "portfolio_context": self.portfolio_repo.get_full_text(request.jobseeker_id),
            "company_introduction_context": self.company_introduction_repo.get_full_text(request.company_id),
            "jd_context": self.recruitment_notice_repo.get_full_text(request.job_group_id),
        }

        # 3. Graph State 초기 상태 구성 (LangGraph 주입용)
        init_state = {
            # 메타데이터
            "jobseeker_id": request.jobseeker_id,
            "company_id": request.company_id,
            "job_group_id": request.job_group_id,
            
            # 진행 상태
            "current_turn": 0,
            "interview_stage": "INTRO",
            "red_flag_count": 0,
            "status": "interview",
            "messages": [], # 초기엔 빈 메시지 리스트
            "evaluation_history": [],

            # 컨텍스트 데이터 병합
            **context_data
        }

        # 4. 에이전트 실행 (첫 질문 생성)
        # session_id를 thread_id로 사용하여 메모리 설정
        try:
            # agent.start_interview 내부에서 interviewer_node -> END 까지 실행됨
            ai_state = await self.agent.start_interview(new_session_id, init_state)
        
        except Exception as e:
            # 에러 발생 시 세션 상태를 ERROR로 변경하고 재전파
            new_session.status = "ERROR"
            self.session_repo.update(new_session)
            print(f"Error occurred during interview: {e}")
            raise HTTPException(status_code=500, detail="면접 시작 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

        # 5. Agent 실행 결과(첫 질문) 결과 처리 및 DB 업데이트
        last_message_content = ""
        if ai_state.get("messages"):
            last_message = ai_state["messages"][-1] # LangChain Message 객체
            last_message_content = last_message.content
            print(f"AI 면접관 질문: {last_message_content}")
            
            # DB의 chat_history(JSON)에 AI의 첫 질문 기록
            # LangGraph의 messages는 객체이므로 JSON 직렬화 가능한 dict로 변환해 저장해야 함
        new_history = [
            {
                "role": "ai", 
                "content": last_message_content, 
                "timestamp": str(datetime.now())
            }
        ]
        new_session.chat_history = new_history

        # 세션 상태 동기화
        new_session.current_turn = ai_state.get("current_turn", 1)
        new_session.interview_stage = ai_state.get("interview_stage", "INTRO")
        
        # DB 업데이트 커밋
        self.session_repo.update(new_session)

        # 6. Response - TTS 변환 후 프론트엔드 반환
        ai_audio_bytes = tts_service.speak(last_message_content) #None

        ai_audio_base64 = None
        if ai_audio_bytes:
            ai_audio_base64 = base64.b64encode(ai_audio_bytes).decode('utf-8')

        return company_ai_interview_response_dto.InterviewResponse(
            message = "200 OK, 인터뷰가 성공적으로 시작됩니다.",
            session_id=new_session_id,
            current_turn=new_session.current_turn,
            interview_stage=new_session.interview_stage,
            ai_message=last_message_content,
            status="interview",
            ai_audio_base64=ai_audio_base64 
        )

    # 인터뷰 진행
    async def process_user_answer(self, session_id: str, user_answer: str) -> company_ai_interview_response_dto.InterviewResponse:   
        """
        사용자의 텍스트 답변을 처리하고, AI의 다음 질문을 반환합니다.
        Flow: DB 조회 -> Agent 실행 -> DB 대화내역 업데이트 -> 결과 반환
        """
        # 1. DB에서 세션 정보 조회
        session_record = self.session_repo.get_by_session_id(session_id)
        
        if not session_record:
            raise HTTPException(status_code=404, detail="해당 ID의 세션을 찾을 수 없습니다.")
        
        if session_record.status == "COMPLETED":
             # 이미 끝난 면접에 접근 시, 마지막 메시지나 종료 알림 반환
             return company_ai_interview_response_dto.InterviewResponse(
                message="200 OK, 해당 ID의 인터뷰는 완료된 면접입니다.",
                session_id=session_id,
                current_turn=session_record.current_turn,
                interview_stage="DONE",
                ai_message="이미 종료된 면접입니다.",
                status="done",
                ai_audio_base64=None
            )
        
        # 2. LangGraph 실행 (답변 주입 -> 평가 -> 질문 생성)
        try:
            # 1) HumanMessage 주입
            # 3) Evaluator -> Interviewer -> END
            ai_state = await self.agent.process_answer(session_id, user_answer)
        except Exception as e:
            print(f"LangGraph 실행 실패: {e}")
            raise HTTPException(status_code=500, detail="AI 응답 생성 중 오류가 발생했습니다.")
        
        # 3. LangGraph 실행 결과를 DB에 업데이트

        # 3-1. 기존 기록 가져오기 (없으면 빈 리스트)
        current_history = session_record.chat_history if session_record.chat_history else []
        
        # 3-2. 유저 답변 기록
        user_entry = {
            "role": "user", 
            "content": user_answer, 
            "timestamp": str(datetime.now())
        }
        current_history.append(user_entry)

        # 3-3. AI 답변 기록 (Agent가 생성한 마지막 메시지)
        last_ai_message = ""
        if ai_state.get("messages"):
            last_ai_message = ai_state["messages"][-1].content
            # AI 답변 출력
            print(f"AI 면접관 질문: {last_ai_message}")

        ai_entry = {
            "role": "ai", 
            "content": last_ai_message, 
            "timestamp": str(datetime.now())
        }
        current_history.append(ai_entry)

        # 3-4. 변경된 리스트를 다시 할당 (SQLAlchemy 감지용)
        session_record.chat_history = list(current_history)

        # 4. 면접 종료 여부 확인 및 처리
        if ai_state.get("status") == "done":
            
            print("면접 종료. 결과 분석 시작.")
            
            # 4-1 세션 상태 업데이트
            session_record.status = "COMPLETED"

            # 4-2. 결과 테이블(Result) 저장
            db_payload = ai_state.get("db_payload")
            if db_payload:
                # 외래키 주입 (어떤 세션의 결과인지)
                db_payload["session_id"] = session_id 
                interview_result = self.interview_repo.create(db_payload)

                created_result_id = interview_result.id
            
            # 면접자 update 로직
            try: 
                # NCS 레벨 가져오기
                jobseeker_ncs_level = self.jobseeker_repo.get_by_id(db_payload.get("jobseeker_id")).ncs_level
                # Talent_type 결정
                ai_rcs_level = db_payload.get("rcs_level")
                talent_type = self._calculate_talent_type(jobseeker_ncs_level, ai_rcs_level)
                print(f"분석된] RCS: {ai_rcs_level} (구직자 NCS: {jobseeker_ncs_level}) 인재 유형: {talent_type}")

                self.jobseeker_repo.update_rcs_and_talent_type(db_payload.get("jobseeker_id"), ai_rcs_level, talent_type)

            except Exception as e:
                print(f"RCS 업데이트 실패: {e}")
            # 4-3. 트랜잭션 커밋
            self.session_repo.update(session_record) # update 내부에서 commit 수행

            closing_ment = "면접이 모두 종료되었습니다. 면접자님 수고하셨습니다. 최종 결과를 확인해주세요."
            ai_audio_bytes = tts_service.speak(closing_ment) # None

            ai_audio_base64 = None
            if ai_audio_bytes:
                ai_audio_base64 = base64.b64encode(ai_audio_bytes).decode('utf-8')

            print(f"\n면접 완료. \nsession_id: {session_id}, \ncurrent_turn: {session_record.current_turn}\ninterview_stage: {session_record.interview_stage}\n")
            return company_ai_interview_response_dto.InterviewResponse(
                message="200 OK, 면접 완료.",
                session_id=session_id,
                current_turn=session_record.current_turn,
                interview_stage="CLOSING",
                ai_message=closing_ment,
                status="done",
                ai_audio_base64=ai_audio_base64,
                interview_result_id=created_result_id
            )

        # 5. Update Session - 진행 중 상태 업데이트
        session_record.current_turn = ai_state.get("current_turn", session_record.current_turn)
        session_record.interview_stage = ai_state.get("interview_stage", session_record.interview_stage)
        
        # DB 저장
        self.session_repo.update(session_record)

        # 6. TTS - (Optional) 음성 변환
        ai_audio_bytes = tts_service.speak(last_ai_message) # None

        ai_audio_base64 = None
        if ai_audio_bytes:
            ai_audio_base64 = base64.b64encode(ai_audio_bytes).decode('utf-8')

        # 7. Response 결과 반환

        print(f"\n인터뷰 진행 중. \nsession_id: {session_id}, \ncurrent_turn: {session_record.current_turn}\ninterview_stage: {session_record.interview_stage}\n")
        return company_ai_interview_response_dto.InterviewResponse(
            message="200 OK, 인터뷰 진행 중.",
            session_id=session_id,
            current_turn=session_record.current_turn,
            interview_stage=session_record.interview_stage,
            ai_message=last_ai_message, # AI의 질문 내용
            status="interview",
            ai_audio_base64=ai_audio_base64
        )


    # 사용자의 음성파일을 받아 STT 실행 후 process_user_answer를 재호출하고 DB에 업데이트
    async def process_voice_answer(self, session_id: str, file: UploadFile) -> company_ai_interview_response_dto.InterviewResponse:
        """
        사용자의 음성 파일을 받아 STT 변환 후, process_user_answer를 재호출합니다.
        Flow: Audio File -> STT -> Text -> process_user_answer()
        """
        # 1. 파일 읽기
        try:
            audio_bytes = await file.read()
        except Exception as e:
            print(f"오디오 파일 읽기 실패: {e}")
            raise HTTPException(status_code=400, detail="오디오 파일을 읽을 수 없습니다.")

        # 2. PCM -> WAV 변환 (필요한 경우에만)
        if file.filename.lower().endswith(".pcm"):
             audio_bytes = pcm_to_wav_bytes(audio_bytes, sample_rate=16000, channels=1)
        
        # 3. STT 변환 (STT 서비스 호출)
        try:
            transcribed_text = stt_service.transcribe(audio_bytes)
            print(f"인식된 텍스트: {transcribed_text}")
        except Exception as e:
            print(f"STT 변환 실패: {e}")
            raise HTTPException(status_code=500, detail="STT 음성 변환에 실패했습니다.")
        
        if not transcribed_text or len(transcribed_text.strip()) == 0:
            raise HTTPException(status_code=400, detail="인식된 텍스트이 없습니다. 다시 말씀해주세요") 

        # 4. 변환된 텍스트로 'process_user_answer' 호출
        return await self.process_user_answer(session_id, transcribed_text)
    
    # 면접을 강제로 종료하고, 현재까지의 대화 내용만을 바탕으로 최종 분석을 수행
    async def force_end_interview(self, session_id: str) -> company_ai_interview_response_dto.InterviewResponse:
        """
        면접을 강제로 종료하고, 현재까지의 대화 내용만을 바탕으로 최종 분석을 수행합니다.
        """
        # 1. 면접 세션 조회
        session_record = self.session_repo.get_by_session_id(session_id)
        if not session_record:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        if session_record.status == "COMPLETED":
             raise HTTPException(status_code=400, detail="이미 종료된 면접입니다.")
        
        # 2. Agent에게 종료 요청
        try:
            ai_state = await self.agent.end_interview(session_id)
        except Exception as e:
            print(f"면접 강제 종료 중 에러 발생: {e}")
            raise HTTPException(status_code=500, detail="면접 강제 중 에러 발생.")

        # 3. 결과 저장 로직 (기존 process_user_answer의 종료 로직과 동일하게 재사용)
            
        print("면접 강제 종료. 결과 분석 시작.")
        
        # 3-1 세션 상태 업데이트
        session_record.status = "COMPLETED"

        # 3-2. 결과 테이블(Result) 저장
        created_result_id = None
        db_payload = ai_state.get("db_payload")

        if db_payload:
            # 외래키 주입 (어떤 세션의 결과인지)
            db_payload["session_id"] = session_id 
            interview_result = self.interview_repo.create(db_payload)

            created_result_id = interview_result.id
        
        # 면접자 update 로직
        try: 
            # NCS 레벨 가져오기
            jobseeker_ncs_level = self.jobseeker_repo.get_by_id(db_payload.get("jobseeker_id")).ncs_level
            # Talent_type 결정
            ai_rcs_level = db_payload.get("rcs_level")
            talent_type = self._calculate_talent_type(jobseeker_ncs_level, ai_rcs_level)
            print(f"분석된] RCS: {ai_rcs_level} (구직자 NCS: {jobseeker_ncs_level}) 인재 유형: {talent_type}")

            self.jobseeker_repo.update_rcs_and_talent_type(db_payload.get("jobseeker_id"), ai_rcs_level, talent_type)

        except Exception as e:
            print(f"RCS 업데이트 실패: {e}")

        # 3-3. 트랜잭션 커밋
        self.session_repo.update(session_record) # update 내부에서 commit 수행

        closing_ment = "면접이 중간에 강제 종료되었습니다. 최종 결과를 확인해주세요."
        ai_audio_bytes = tts_service.speak(closing_ment) # None

        ai_audio_base64 = None
        if ai_audio_bytes:
            ai_audio_base64 = base64.b64encode(ai_audio_bytes).decode('utf-8')

        return company_ai_interview_response_dto.InterviewResponse(
            message="200 OK, 면접 완료.",
            session_id=session_id,
            current_turn=session_record.current_turn,
            interview_stage="CLOSING",
            ai_message=closing_ment,
            status="done",
            ai_audio_base64=ai_audio_base64,
            interview_result_id=created_result_id
        )
    
    # 인터뷰 결과를 반환
    async def get_interview_result_by_interview_id(self, company_ai_interview_id: int) -> company_ai_interview_response_dto.InterviewResultResponse:
        interview_result_row = self.interview_repo.get_with_details_by_id(company_ai_interview_id)
        if not interview_result_row:
            raise HTTPException(status_code=404, detail="해당 id의 InterviewResult를 찾을 수 없습니다.")

        interview_result = interview_result_row.CompanyAIInterview  # 엔티티 객체
        jobseeker_name = interview_result_row.jobseeker_name        # .label("jobseeker_name")으로 지정한 값
        company_name = interview_result_row.company_name
        job_group_name = interview_result_row.job_group_name
        jobseeker_email = interview_result_row.jobseeker_email

        # 날짜 포맷팅 로직 (YYYY.MM.DD HH:MM 형식)
        formatted_end_time = None
        if interview_result.end_time:
            formatted_end_time = interview_result.end_time.strftime("%Y.%m.%d %H:%M")

        return company_ai_interview_response_dto.InterviewResultResponse(
            message="200 OK, 인터뷰 결과.",
            interview_id = company_ai_interview_id,
            session_id=interview_result.session_id,
            jobseeker_id = interview_result.jobseeker_id,
            job_group_id = interview_result.job_group_id,
            jobseeker_name = jobseeker_name,
            company_name = company_name,
            job_group_name = job_group_name,
            jobseeker_email = jobseeker_email, 
            report = interview_result.report,
            summary = interview_result.summary,
            total_score = interview_result.total_score,
            skills_evaluation = interview_result.skills_evaluation,
            ai_result = interview_result.ai_result,
            best_answer = interview_result.best_answer,
            worst_answer = interview_result.worst_answer,
            total_advice = interview_result.total_advice,
            better_answer_list = interview_result.better_answer_list or [],
            end_time = formatted_end_time
        )
        
    def _calculate_talent_type(self, ncs_level: int, rcs_level: int) -> str:
        if ncs_level >= 6 and rcs_level >= 6:
            return "PROVEN_ACE"
        if ncs_level + 2 <= rcs_level:
            return "HIDDEN_GEM"
        if ncs_level -2 >= rcs_level:
            return "BUBBLE"
        return "LEARNER"
    
    async def send_interview_report_to_email(self, email, subject, html_content, background_tasks: BackgroundTasks):
        # CSS 인라인 변환
        inline_html = transform(html_content)

        # 메일 메시지 구성
        message = MessageSchema(
            subject=subject,
            recipients=email,
            body=inline_html,
            subtype=MessageType.html
        )

        conf = ConnectionConfig(
            MAIL_USERNAME=settings.MAIL_USERNAME,
            MAIL_PASSWORD=settings.MAIL_PASSWORD,    
            MAIL_FROM=settings.MAIL_FROM,
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=settings.MAIL_SERVER,    
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=settings.USE_CREDENTIALS,
            VALIDATE_CERTS=settings.VALIDATE_CERTS
        )

        # 메일 발송 객체
        fm = FastMail(conf)

        # 사용자를 기다리게 하지 않고 백그라운드에서 전송
        background_tasks.add_task(fm.send_message, message)

        return "200 OK, 메일 발송 완료."