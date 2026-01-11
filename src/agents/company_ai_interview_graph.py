# Copyright (c) 2026.01.11 ReNe
# Author: 이연(Yeon Lee)

from typing import Annotated, List, TypedDict, Union, Optional, Literal, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import os, sys
from typing import Literal
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import aiosqlite
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from pathlib import Path    
from dotenv import load_dotenv
import json
load_dotenv()

current_path = Path(__file__).resolve()
PROJECT_ROOT = current_path.parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "sqlite_saver" / "company_ai_interview_state.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# === 상태 정의 ===
class InterviewState(TypedDict):
    # 대화 기록 (Langraph가 자동으로 append 처리)
    messages: Annotated[List[BaseMessage], add_messages] # 대화 기록
    status: Literal["interview", "evaluate", "done"]
    current_turn: int # 현재 턴수
    red_flag_count: int # 연속 실패 횟수(조기 종료용)

    # RAG 검색용 메타데이터
    jobseeker_id: int # 구직자 ID
    company_id: int # 기업 ID
    job_group_id: int # 직군 ID
    company_name: str
    jobseeker_name: str
    company_info: str # ChromaDB에서 가져온 기업 정보
    jobseeker_info: str # ChromaDB에서 가져온 구직자 정보
    resume_context: str
    portfolio_context: str
    company_introduction_context: str
    jd_context: str

    # 면접 단계용 필드
    interview_stage: str # "INTRO", "TECH", "BEHAVIORAL", "CLOSING"

    # 평가 데이터 (DB 저장용)
    evaluation_history: List[dict]

    # 최종 리포트 데이터 (Analyst 결과)
    final_result: Optional[dict] # Analyst 결과
    db_payload: Optional[dict] # DB 삽입용 정리된 데이터  

# 평가 노드 출력 데이터 구조 정의 (Pydantic)
class EvaluationOutput(BaseModel):
    score: int = Field(description="0에서 10 사이의 정수 답변 점수")
    result: str = Field(description="평가 결과: PASS, WEAK, FAIL 중 하나")
    reason: str = Field(description="평가 근거 (한국어)")
    follow_up_needed: bool = Field(description="꼬리 질문 필요 여부 (True/False)")
    # 더 나은 답변 필드 추가
    better_answer: str = Field(description="지원자의 답변을 보완하여 더 논리적이고 구체적으로 개선한 모범 답변")

class QnAFeedback(BaseModel):
    question: str
    user_answer: str
    better_answer: str
    score: int

# 최종 평가를 위한 서브 모델 정의
class SkillDetail(BaseModel):
    skill_name: str = Field(description="기술 스택 이름 (예: Python, AWS, 문제해결능력 등)")
    score: int = Field(description="기술 수준 등급 (1~8 사이의 정수)")
    reason: str = Field(description="해당 등급을 부여한 구체적인 평가 사유")

# 최종 분석 & 평가를 위한 모델 정의
class FinalAnalystOutput(BaseModel):
    final_score: float = Field(description="종합 점수 (0-100)")
    interview_result: str = Field(description="PASS, HOLD, FAIL 중 하나")
    summary: str = Field(description="면접 한 줄 요약")
    detailed_report: str = Field(description="면접 상세 보고서")
    skills_evaluation: List[SkillDetail] = Field(description="검증된 기술들에 대한 상세 평가 리스트")
    best_answer: str = Field(description="면접자의 최고의 답변 내용 - 최고의 답변인 이유")
    worst_answer: str = Field(description="면접자의 최악의 답변 내용 - 최악의 답변인 이유")
    total_feedback_for_jobseeker: str = Field(description="지원자에게 줄 AI의 피드백")
    rcs_level: int = Field(description="RCS 점수 (1~8 사이의 정수)")


# === Agent Class ===
class CompanyAIInterviewAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
        self.db_path = str(DB_PATH)
        self.graph_builder = self._build_graph()

    def _load_prompt(self, filename: str) -> str:
        """프롬프트 파일 로드 안전 장치"""
        path = PROJECT_ROOT / "src" / "prompts" / filename
        # 파일이 없을 경우 대비한 기본값 또는 에러 처리
        if not path.exists():
            # 개발/테스트 환경을 위해 fallback 처리 (실제 배포시는 에러 raise 권장)
            return "당신은 AI 면접관입니다." 
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    # --- Nodes ---
    def interviewer_node(self, state: InterviewState) -> Dict[str, Any]:
        print(f"\n [Interview] 질문 생성 중 (Turn: {state.get('current_turn', 0)})")
        
        system_prompt = self._load_prompt("company_ai_interview_prompt_ver2.0.md")
        current_turn = state.get("current_turn", 0)
        eval_history = state.get("evaluation_history", [])
        print(f"현재 턴수 : {current_turn}")
        # 스테이지 결정 로직
        current_stage = state.get("interview_stage", "INTRO")
        if current_turn <= 1:
            current_stage = "INTRO"
        elif 1 < current_turn <= 3:
            current_stage = "RESUME_VERIFICATION"
        elif 3 < current_turn <= 6:
            current_stage = "TECH_SCREENING"
        elif 6 < current_turn <= 8:
            current_stage = "CULTURE_FIT"
        elif current_turn == 9:
            current_stage = "LAST_COMMENTS" # [NEW] 마지막 발언 기회
        elif current_turn >= 10:
            current_stage = "CLOSING"       # [NEW] 진짜 종료 인사
        
        # 지침 설정
        is_stage_change_turn = current_turn in [2, 5, 8] # 예: 스테이지가 바뀌는 턴

        last_eval = eval_history[-1]["eval"] if eval_history else {}
        # if last_eval.get("follow_up_needed") and not is_stage_change_turn:
        #     guidance = "!지침: 이전 답변이 불충분합니다. 압박 질문(Probing Question)을 던지세요."
        # else:
        guidance = f"지침: 현재 스테이지[{current_stage}]에 알맞은 새로운 질문을 던지세요."

        rag_context = f"""
        [기업 정보] 
        {state.get('company_info')}
        [지원자 정보] 
        {state.get('jobseeker_info')}
        [이력서] 
        {state.get('resume_context')}
        [포트폴리오]
        {state.get('portfolio_context')}
        [기업 소개서]
        {state.get('company_introduction_context')}
        [채용공고] 
        {state.get('jd_context')}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt + "\n\n" + rag_context),
            ("system", f"현재 상황: {guidance}"),
            ("placeholder", "{messages}")
        ])

        chain = prompt | self.llm
        response = chain.invoke({
            "company_name": state.get("company_name"),
            "job_group_name": state.get("job_group_name"),
            "user_name": state.get("jobseeker_name"),
            "current_stage": current_stage,
            "last_evaluation_result": last_eval.get("result", "NONE"),
            "follow_up_needed": last_eval.get("follow_up_needed", False),
            "ncs_level": 4,
            "messages": state["messages"]
        })

        return {
            "messages": [response],
            "current_turn": current_turn + 1,
            "interview_stage": current_stage
        }   


    def strict_evaluator_node(self, state: InterviewState) -> Dict[str, Any]:
        print(f"\n [Evaluator] 답변 평가 중")
        messages = state["messages"]
        # 메시지가 충분하지 않으면(시작 시점 등) 스킵
        if len(messages) < 2: return {}

        last_human_msg = messages[-1].content
        last_ai_msg = messages[-2].content

        evaluate_prompt = self._load_prompt("strict_evaluator.md")
        parser = PydanticOutputParser(pydantic_object=EvaluationOutput)

        prompt = ChatPromptTemplate.from_messages([
            ("system", evaluate_prompt),
            ("system", "JSON 형식 준수:\n{format_instructions}"),
            ("human", f"질문: {last_ai_msg}\n답변: {last_human_msg}") 
        ])

        chain = prompt | self.llm | parser
        
        try:
            eval_result = chain.invoke({
                "question_text":last_ai_msg,
                "answer_text": last_human_msg,
                "jd_context": state.get("jd_context", ""),
                "resume_context": state.get("resume_context", ""),
                "format_instructions": parser.get_format_instructions()
            })
            eval_dict = eval_result.dict()

            eval_dict["question"] = last_ai_msg
            eval_dict["user_answer"] = last_human_msg
            
        except Exception as e:
            print(f"평가 파싱 에러: {e}")
            eval_dict = {
                "score": 5, "result": "WEAK", "reason": "Parsing Error", "follow_up_needed": False,
                "better_answer": "평가 중 오류가 발생하여 모범 답안을 생성하지 못했습니다.",
                "question": last_ai_msg,
                "user_answer": last_human_msg
            }

        # RED FLAG 업데이트
        score = eval_dict.get("score", 5)
        result = eval_dict.get("result", "WEAK")
        current_flag = state.get("red_flag_count", 0)

        if result == 'FAIL':
            new_current_flag =  current_flag + 1
            print(f"답변에서 결격 사유 감지. (점수: {score}점, 연속 {new_current_flag}회)")
        else:
            new_current_flag = 0
            if result == "WEAK":
                print(f"[WEAK] 추가 검증 필요 (점수: {score}점) -> 레드 플래그 초기화됨")
            else:
                print(f"[PASS] 통과 (점수: {score}점) -> 레드 플래그 초기화됨")

        new_entry = {
            "turn": state.get("current_turn"),
            "stage": state.get("interview_stage"),
            # "question": last_ai_msg,
            # "answer": last_human_msg,
            "eval": eval_dict
        }

        return {
            "red_flag_count": new_current_flag,
            "evaluation_history": state.get("evaluation_history", []) + [new_entry]
        }
    
    def final_analyzer_node(self, state: InterviewState) -> Dict[str, Any]:
        print("\n [Analyze] 최종 분석 중")
        # ... (기존 로직과 동일, Payload 구성) ...
        transcript = "\n".join([f"{msg.type}: {msg.content}" for msg in state["messages"]])
        
        # 앞선 평가 히스토리 문자열로 반환
        eval_history = state.get("evaluation_history", [])
        eval_history_str = json.dumps(eval_history, ensure_ascii=False, indent=2)

        parser = PydanticOutputParser(pydantic_object=FinalAnalystOutput)
        analyst_prompt = self._load_prompt("final_analyst.md")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", analyst_prompt),
            ("system", "반드시 다음 형식 요구사항을 준수하여 JSON만 출력하세요:\n{format_instructions}"),
            ("human", "[전체 면접 기록]\n{full_transcript}"),
        ])
        
        chain = prompt | self.llm | parser
        
        try:
            final_result = chain.invoke({
                "full_transcript": transcript,
                "company_name": state.get("company_name", ""),
                "jobseeker_name": state.get("jobseeker_name", ""),
                "jd_context": state.get("jd_context", ""),
                "evaluation_history_context": eval_history_str,
                "format_instructions": parser.get_format_instructions()
            })
            final_result = final_result.dict()

        except Exception as e:
            print(f"최종 분석 중 예외 발생: {e}")
            # 에러 발생 시 기본값
            final_result = {
                "final_score": 0.0,
                "interview_result": "HOLD",
                "summary": "분석 오류",
                "detailed_report": "오류 발생",
                "skills_evaluation": [], # 빈 리스트
                "best_answer": "-",
                "worst_answer": "-",
                "total_feedback_for_jobseeker": "-",
                "rcs_level": 1,
            }

        # DB Payload 구성

        qna_feedback_list = []

        for entry in state.get("evaluation_history", []):
            eval_data = entry.get("eval", {})

            if "better_answer" in eval_data:
                qna_feedback_list.append({
                    "question": eval_data.get("question", ""),
                    "user_answer": eval_data.get("user_answer", ""),
                    "better_answer": eval_data.get("better_answer", ""),
                    "score": eval_data.get("score", 0)
                })

        db_payload = {
            "jobseeker_id": state.get("jobseeker_id", 1),
            "job_group_id": state.get("job_group_id", 1),
            "report": final_result["detailed_report"],
            "summary": final_result["summary"],
            "total_score": final_result["final_score"],
            "ai_result": final_result["interview_result"],
            "best_answer": final_result["best_answer"],
            "worst_answer": final_result["worst_answer"],
            "total_advice": final_result["total_feedback_for_jobseeker"],
            "rcs_level": final_result["rcs_level"],
            
            # DB의 skills_evaluation 컬럼은 JSON 타입이므로 리스트(List[dict]) 그대로 저장하면 됩니다.
            "skills_evaluation": final_result["skills_evaluation"],
            "full_transcript": transcript,
            "better_answer_list": qna_feedback_list
        }
            
        return {
        "final_result": final_result,
        "db_payload": db_payload,
        "status": "done"
    }

    # === Routing ===
    def start_route(self, state: InterviewState) -> Literal["interviewer_node", "strict_evaluator_node"]:
        """시작 시점 라우팅: 유저 메시지가 있으면 평가부터, 없으면 질문부터"""
        messages = state.get("messages", [])
        if messages and isinstance(messages[-1], HumanMessage):
            return "strict_evaluator_node"
        return "interviewer_node"

    def mid_route(self, state: InterviewState) -> Literal["interviewer_node", "final_analyzer_node"]:
        """평가 후 라우팅"""
        if state.get("red_flag_count", 0) >= 3:
            return "final_analyzer_node"
        if state.get("current_turn") == 11:
            return "final_analyzer_node"
        return "interviewer_node"
    
    def _build_graph(self):
        workflow = StateGraph(InterviewState)
        
        workflow.add_node("interviewer_node", self.interviewer_node)
        workflow.add_node("strict_evaluator_node", self.strict_evaluator_node)
        workflow.add_node("final_analyzer_node", self.final_analyzer_node)

        # 시작 -> 조건부 분기 (첫 질문이냐 답변이냐)
        workflow.add_conditional_edges(START, self.start_route)
        
        # 질문 -> 유저 입력 대기 (END)
        workflow.add_edge("interviewer_node", END)
        
        # 평가 -> 조건부 분기 (다음 질문 or 종료)
        workflow.add_conditional_edges("strict_evaluator_node", self.mid_route)
        
        # 분석 -> 종료
        workflow.add_edge("final_analyzer_node", END)

        return workflow
    
    # === Service Methods ===
    async def start_interview(self, session_id: str, initial_state: dict):
        """첫 질문 생성"""
        config = {"configurable": {"thread_id": session_id}}

        # 실행 시점에 DB 연결 -> 컴파일 -> 실행
        async with aiosqlite.connect(self.db_path) as conn:
            conn.is_alive = lambda: True
            checkpointer = AsyncSqliteSaver(conn)
            
            graph = self.graph_builder.compile(checkpointer=checkpointer)
            return await graph.ainvoke(initial_state, config)
    
    async def process_answer(self, session_id: str, user_answer: str):
        """답변 처리 및 다음 질문 생성"""
        config = {"configurable": {"thread_id": session_id}}

        # 실행 시점에 DB 연결 -> 컴파일 -> 실행
        async with aiosqlite.connect(self.db_path) as conn:
            conn.is_alive = lambda: True
            checkpointer = AsyncSqliteSaver(conn)
            graph = self.graph_builder.compile(checkpointer=checkpointer)
            
            input_message = HumanMessage(content=user_answer)
            await graph.aupdate_state(config, {"messages": [input_message]})

            # 그래프 실행 (None을 주면 현재 상태에서 이어서 실행 -> start_route가 Evaluator로 보냄)
            # invoke(None) 호출하면 원래 START부터 다시 시작하지만 start_route 로직에 의해 메시지가 있으면 Evaluator로 이동
            return await graph.ainvoke({"messages": [input_message]}, config)

    
    async def end_interview(self, session_id: str):
        """
        [강제 종료] 현재 상태를 'CLOSING'으로 강제 변경하고,
        곧바로 최종 분석(Analyst) 노드를 실행하여 결과를 반환합니다.
        """
        config = {"configurable": {"thread_id": session_id}}

        async with aiosqlite.connect(self.db_path) as conn:
            # 1. 연결 및 패치
            conn.is_alive = lambda: True
            checkpointer = AsyncSqliteSaver(conn)
            graph = self.graph_builder.compile(checkpointer=checkpointer)

            # 2. 상태 강제 업데이트 (라우팅 로직을 속이기 위해)
            # interview_stage를 CLOSING으로 바꾸고 혹시 모르니 red_flag도 강제 종료 조건 충족
            update_values = {
                "interview_stage": "CLOSING",
                "red_flag_count": 3,
            } 

            # red_flag_count를 3로 바꾸고, interview_stage를 CLOSING으로 바꾸기
            await graph.aupdate_state(config, update_values)

            input_message = "면접 종료"
            # 3. 그래프 실행
            return await graph.ainvoke({"messages": [input_message]}, config)