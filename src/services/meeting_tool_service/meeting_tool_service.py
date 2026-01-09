#모듈 정의 : 회의록 자동 생성 및 Google Sheets 연동 - Service Module
#연결 모듈 : src/api/endpoints/meeting_tool/meeting_tool_app.py (API),
#  src/utils/google_utils.py (Utils)
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
# LangChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from utils.google_utils import MimeType, mkfile, auth, append_datas_to_spreadsheet, GResult

# 분리한 프롬프트 임포트
from prompts.meeting_tool_prompts import TEAM_MEETING_SYSTEM_PROMPT, MENTORING_SYSTEM_PROMPT

# --- 설정 ---
load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini", 
    temperature=0, 
)

current_path = Path(__file__).resolve()
# 프로젝트 루트 경로 설정
PROJECT_ROOT = current_path.parent.parent.parent
CREDENTIALS_FILE_PATH = PROJECT_ROOT / 'credentials.json'
SHEET_NAME = 'Notes'
SPREADSHEET_PATH_NAME = 'Daily Mentoring Notes(언리얼 트랙 & AI 트랙 융합_6조)'

def _parse_with_open_ai(content: str, system_prompt: str) -> dict:
    """공통적인 회의 데이터 JSON 파싱 로직"""
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", '{content}')
    ])

    chain = chat_prompt | llm | JsonOutputParser()
    return chain.invoke({"content": content})

def format_for_tasks(task_list: list) -> str:
    """ 리스트 데이터를 - (작업 이름) 작업 내용 형식으로 변환 """
    if not task_list: return ""
    if isinstance(task_list, dict): task_list = [task_list]

    formatted_lines = []
    for item in task_list:
        name = item.get('name', '').strip()
        task = item.get('task', '').strip()

        if name or task:
            formatted_lines.append(f"- ({name}) {task}")

    return "\n".join(formatted_lines)

def _update_sheet(rows: list) -> dict:
    """ 구글 시트에 업데이트 하는 공통 헬퍼 함수"""
    try:
        creds = auth(credentials_file=CREDENTIALS_FILE_PATH)
        file_result = mkfile(creds, SPREADSHEET_PATH_NAME, MimeType.spreadsheet)

        if not file_result.id:
            raise Exception("Daily Mentoring Notes 파일을 찾거나 생성할 수 없습니다.")
        
        result = append_datas_to_spreadsheet(creds, file_result.id, SHEET_NAME, rows)

        return {
            "status": "success",
            "result": result.result,
            "message": result.message,
            "id": result.id
        }
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {"status": "error", "message": str(e)}

def process_team_meeting(content: str) -> dict:
    """ 팀 회의록 처리 로직 """
    # 1. LLM 으로 JSON 파싱
    response = _parse_with_open_ai(content, TEAM_MEETING_SYSTEM_PROMPT)

    # 2. 데이터 가공 & 포맷팅
    rows_to_add = []

    # 전역
    gb_data = response.get('global', {})
    rows_to_add.append([
        gb_data.get('일자', ''),
        '전역', # 구분
        gb_data.get('DONE', ''),
        gb_data.get('TO DO', ''),
        gb_data.get('ISSUE', ''),
    ])

    # AI
    ai_data = response.get('ai_team', {})
    rows_to_add.append([
        ai_data.get('일자', ''),
        'AI', # 구분
        format_for_tasks(ai_data.get('DONE', [])),
        format_for_tasks(ai_data.get('TO DO', [])),
        format_for_tasks(ai_data.get('ISSUE', [])),
    ])

    # 언리얼
    ue_data = response.get('unreal_team', {})
    rows_to_add.append([
        ue_data.get('일자', ''),
        '언리얼', # 구분
        format_for_tasks(ue_data.get('DONE', [])),
        format_for_tasks(ue_data.get('TO DO', [])),
        format_for_tasks(ue_data.get('ISSUE', [])),
    ])

    # 3. 시트에 업데이트
    return _update_sheet(rows_to_add)

def process_mentoring(content: str) -> dict:
    """ 멘토링 회의록 처리 로직 """
    # 1. LLM 으로 JSON 파싱
    response = _parse_with_open_ai(content, MENTORING_SYSTEM_PROMPT)

    # 2. 데이터 가공 & 포맷팅
    rows_to_add = []

    # 멘토링
    mentoring_data = response.get('mentoring', {})
    rows_to_add.append([
        mentoring_data.get('일자', ''),
        '멘토링', # 구분
        format_for_tasks(mentoring_data.get('DONE', [])),
        format_for_tasks(mentoring_data.get('TO DO', [])),
        format_for_tasks(mentoring_data.get('ISSUE', [])),
    ])

    # 3. 시트에 업데이트
    return _update_sheet(rows_to_add)
