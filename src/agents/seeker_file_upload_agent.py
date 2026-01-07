"""이력서/포트폴리오 파싱 AI 에이전트"""
import os
import sys
import re
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# 프롬프트 임포트
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from prompts.seeker_file_upload_tool_prompts import (
    SEEKER_SCANNER_SYSTEM_PROMPT,
    SEEKER_ANALYSIS_SYSTEM_PROMPT
)
from core.config import settings


def parse_resume_with_llm(text_content: str, file_type: str = "resume") -> Dict[str, Any]:
    """
    LLM을 사용하여 이력서/포트폴리오 텍스트를 구조화된 Markdown으로 파싱 (2-Step Pipeline)
    
    Args:
        text_content: 파일에서 추출한 텍스트
        file_type: 파일 타입 ("resume" 또는 "portfolio")
    
    Returns:
        Dict[str, Any]: 파싱 결과
            - ncs_level: NCS 레벨
            - rcs_level: RCS 레벨
            - markdown_content: 최종 분석된 마크다운 텍스트 (Analyzer Output)
            - parsed_data: 구조화된 데이터 (섹션별 추출)
    
    Raises:
        Exception: LLM 호출 실패 또는 파싱 실패 시
    """
    try:
        # LLM 초기화
        llm = ChatOpenAI(
            model = "gpt-4.1-mini", # 성능과 비용 고려
            temperature = 0.0, # 정해진 포맷 준수를 위해 0으로 설정
            api_key = settings.OPENAI_API_KEY
        )
        
        # --- Step 1: Scanner (Structure & Normalize) ---
        print(f"[Agent] Step 1: Scanner 시작... (Raw Text 길이: {len(text_content)} 자)")
        scanner_messages = [
            SystemMessage(content=SEEKER_SCANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"Raw Resume Text:\n\n{text_content}")
        ]
        scanner_response = llm.invoke(scanner_messages)
        structured_resume = scanner_response.content.strip()
        print(f"[Agent] Step 1 완료. (Structured Resume 길이: {len(structured_resume)} 자)")
        
        # --- Step 2: Analyzer (Logic & Reasoning) ---
        print(f"[Agent] Step 2: Analyzer 시작...")
        analyzer_messages = [
            SystemMessage(content=SEEKER_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=f"Structured Resume Markdown:\n\n{structured_resume}")
        ]
        analyzer_response = llm.invoke(analyzer_messages)
        final_analysis_md = analyzer_response.content.strip()
        
        # Markdown 코드 블록 제거
        final_analysis_md = re.sub(r'^```markdown\s*\n', '', final_analysis_md, flags = re.MULTILINE)
        final_analysis_md = re.sub(r'\n```\s*$', '', final_analysis_md, flags = re.MULTILINE)
        
        print(f"[Agent] Step 2 완료! (Final Analysis 길이: {len(final_analysis_md)} 자)")
        
        # NCS/RCS 레벨 추출
        ncs_level = extract_ncs_level(final_analysis_md)
        rcs_level = extract_rcs_level(final_analysis_md)
        talent_type = extract_talent_type(final_analysis_md)
        
        # 섹션별 데이터 파싱 (Analyzer 결과 기반)
        parsed_data = parse_markdown_sections(final_analysis_md)
        
        return {
            "ncs_level": ncs_level,
            "rcs_level": rcs_level,
            "talent_type": talent_type,
            "markdown_content": final_analysis_md,
            "parsed_data": parsed_data
        }
    
    except Exception as e:
        print(f"[Agent Error] LLM 파싱 실패: {e}")
        raise Exception(f"이력서 파싱 중 오류 발생: {str(e)}")


def extract_ncs_level(markdown_text: str) -> str:
    """
    Markdown에서 NCS 레벨 추출
    Format: - **NCS Level:** **Lv. {N}** (or without bold)
    """
    # **Lv. {N}** 또는 Lv. {N} 모두 허용하고, 뒤에 괄호나 문자가 와도 처리
    pattern = r'-\s*\*\*NCS Level:\*\*\s*(?:\*\*)?(.+?)(?:\*\*|\s*\(|$)'
    match = re.search(pattern, markdown_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Unknown"


def extract_rcs_level(markdown_text: str) -> str:
    """
    Markdown에서 RCS 레벨 추출
    Format: - **RCS Level:** **Lv. {M}** (or without bold)
    """
    pattern = r'-\s*\*\*RCS Level:\*\*\s*(?:\*\*)?(.+?)(?:\*\*|\s*\(|$)'
    match = re.search(pattern, markdown_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Unknown"


def extract_talent_type(markdown_text: str) -> str:
    """
    Markdown에서 Talent Type 추출
    Format: - **Talent Type:** **{TYPE}** (or without bold)
    """
    pattern = r'-\s*\*\*Talent Type:\*\*\s*(?:\*\*)?(.+?)(?:\*\*|\s*\(|$)'
    match = re.search(pattern, markdown_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "LEARNER" # 기본값


def parse_markdown_sections(markdown_text: str) -> Dict[str, Any]:
    """
    Analyzer 결과 Markdown을 섹션별로 파싱
    
    Sections:
    1. [Step 1: Portfolio & Tech Context Analysis]
    2. [Step 2: Skill Assessment & Reasoning]
    3. [Step 3: Final Analysis Summary]
    """
    # 1. 섹션 텍스트 추출
    step1_text = extract_section(markdown_text, r'## \[Step 1: Portfolio & Tech Context Analysis\](.*?)## \[Step 2', re.DOTALL)
    step2_text = extract_section(markdown_text, r'## \[Step 2: Skill Assessment & Reasoning\](.*?)## \[Step 3', re.DOTALL)
    step3_text = extract_section(markdown_text, r'## \[Step 3: Final Analysis Summary\](.*?)$', re.DOTALL)
    
    # 2. 구조화된 데이터 추출
    skills = extract_skills(step2_text)
    
    # Step 3에서 기본 정보 추출
    education = extract_education(step3_text)
    # History는 Step 3에 요약되어 있음
    work_experience = extract_history(step3_text)
    
    # Step 1에서 프로젝트 상세 추출
    project_details = extract_portfolio(step1_text)
    
    # 3. 결과 구성
    parsed_data = {
        "basic_info": step3_text,
        "summary": extract_summary_line(step3_text),
        "hard_facts": step2_text, # Skill Assessment를 Hard Facts로 매핑
        "history": step3_text,
        "portfolio": step1_text,
        
        # 구조화된 데이터 (DB 저장용)
        "skills": skills,
        "main_skills": skills,
        "education": education,
        "certifications": [], # Analyzer 출력에 명시되지 않음 (추후 보완 필요)
        "work_experience": work_experience,
        "project_details": project_details,
        
        "brief_self_introduction": extract_summary_line(step3_text),
        "brief_project_introduction": [],
        "other_experience": [],
        "languages": []
    }
    
    return parsed_data


def extract_skills(text: str) -> list:
    """
    Step 2 섹션에서 스킬 및 레벨 추출
    Format: - **[Category] Name (Lv.X)**
              - *Reasoning:* ...
    """
    skills = []
    
    # Regex Patterns (Priority Order)
    patterns = [
        # 1. Strict: - **[Category] Name (Lv.N)**
        r'-\s*\*\*\[(.*?)\]\s*(.*?)\s*\(Lv\.(\d+)\)\*\*',
        # 2. No Category: - **Name (Lv.N)**
        r'-\s*\*\*(.*?)\s*\(Lv\.(\d+)\)\*\*',
        # 3. Loose (No Bold): - [Category] Name (Lv.N)
        r'-\s*\[(.*?)\]\s*(.*?)\s*\(Lv\.(\d+)\)',
        # 4. Loose (No Bold, No Category): - Name (Lv.N)
        r'-\s*(.*?)\s*\(Lv\.(\d+)\)'
    ]
    
    # Split text into lines to process line by line (safer for mixed formats)
    lines = text.split('\n')
    current_skill = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # Check for Skill Line
        matched = False
        for idx, pattern in enumerate(patterns):
            match = re.search(pattern, line)
            if match:
                # Extract data based on pattern groups
                if idx == 0 or idx == 2: # Has Category
                    category = match.group(1).strip()
                    name = match.group(2).strip()
                    level = int(match.group(3))
                else: # No Category
                    category = "General"
                    name = match.group(1).strip()
                    level = int(match.group(2))
                
                # Save previous skill if exists
                if current_skill:
                    skills.append(current_skill)
                
                # Start new skill
                current_skill = {
                    "name": normalize_skill_name(name),
                    "category": category,
                    "ncs_level": level,
                    "rcs_level": level,
                    "is_verified": False,
                    "reasoning": ""
                }
                matched = True
                break
        
        # Check for Reasoning Line (if inside a skill block)
        if not matched and current_skill and line.startswith("- *Reasoning:*"):
            reasoning = line.replace("- *Reasoning:*", "").strip()
            current_skill["reasoning"] = reasoning
            
    # Append the last skill
    if current_skill:
        skills.append(current_skill)
            
    # Remove duplicates (keep highest level)
    unique_skills = {}
    for skill in skills:
        name = skill["name"]
        if name not in unique_skills or skill["ncs_level"] > unique_skills[name]["ncs_level"]:
            unique_skills[name] = skill
            
    return list(unique_skills.values())

def normalize_skill_name(name: str) -> str:
    """
    스킬명 정규화 (간단한 매핑)
    추후 별도 모듈이나 DB로 관리 필요
    """
    name_lower = name.lower()
    mapping = {
        "react.js": "React",
        "reactjs": "React",
        "vue.js": "Vue.js",
        "vuejs": "Vue.js",
        "node.js": "Node.js",
        "nodejs": "Node.js",
        "spring boot": "Spring Boot",
        "springboot": "Spring Boot",
        "aws": "AWS",
        "amazon web services": "AWS"
    }
    return mapping.get(name_lower, name)


def extract_education(text: str) -> list:
    """Step 3 섹션에서 학력 추출"""
    education_list = []
    
    # Education 섹션 찾기
    # Format:
    # - **Education:**
    #   - {School} ({Major}, {Period})
    
    section_match = re.search(r'-\s*\*\*Education:\*\*(.*?)(?=-\s*\*\*|$)', text, re.DOTALL)
    if not section_match:
        # Fallback for single line format: - **Education:** {Content}
        pattern = r'-\s*\*\*Education:\*\*\s*(.+)'
        match = re.search(pattern, text)
        if match:
            return [match.group(1).strip()]
        return []
        
    content = section_match.group(1)
    
    # 리스트 아이템 파싱
    pattern = r'-\s*(.+)'
    matches = re.finditer(pattern, content)
    
    for match in matches:
        education_list.append(match.group(1).strip())
        
    return education_list


def extract_certifications(text: str) -> list:
    """Step 3 섹션에서 자격증 추출"""
    cert_list = []
    
    # Certifications 섹션 찾기
    # Format:
    # - **Certifications:**
    #   - {Certification Name} ({Date})
    
    section_match = re.search(r'-\s*\*\*Certifications:\*\*(.*?)(?=-\s*\*\*|$)', text, re.DOTALL)
    if not section_match:
        return []
        
    content = section_match.group(1)
    
    # 리스트 아이템 파싱
    pattern = r'-\s*(.+)'
    matches = re.finditer(pattern, content)
    
    for match in matches:
        cert_list.append(match.group(1).strip())
        
    return cert_list


def extract_history(text: str) -> list:
    """Step 3 섹션에서 경력 추출"""
    history_list = []
    # Format:
    # - **History:**
    #   1. {Company} ({Period})
    
    # History 섹션 찾기
    history_section_match = re.search(r'-\s*\*\*History:\*\*(.*)', text, re.DOTALL)
    if not history_section_match:
        return []
        
    history_content = history_section_match.group(1)
    
    # 숫자 리스트 파싱: 1. Company (Period)
    pattern = r'\d+\.\s*(.*?)\s*\((.*?)\)'
    matches = re.finditer(pattern, history_content)
    
    for match in matches:
        company_name = match.group(1).strip()
        period = match.group(2).strip()
        
        history_list.append({
            "company_name": company_name,
            "period": period,
            "role": "Unknown" # 요약본에는 Role이 없을 수 있음
        })
        
    return history_list


def extract_portfolio(text: str) -> list:
    """Step 1 섹션에서 프로젝트 추출"""
    project_list = []
    # Format:
    # ### 1. {Project Name}
    # - **Role:** ...
    
    pattern = r'### \d+\.\s+(.*?)\n(.*?)(?=### \d+\.|$)'
    matches = re.finditer(pattern, text, re.DOTALL)
    
    for match in matches:
        project_name = match.group(1).strip()
        content = match.group(2).strip()
        
        position_match = re.search(r'-\s*\*\*Role:\*\*\s*(.*)', content)
        
        # Tech Context & Achievement 추출
        # 간단히 전체 내용을 description으로 저장
        description = content
        
        project_list.append({
            "project_name": project_name,
            "position": position_match.group(1).strip() if position_match else "",
            "description": description
        })
        
    return project_list


def extract_summary_line(text: str) -> str:
    """Basic Info에서 Summary 추출"""
    match = re.search(r'-\s*\*\*Summary:\*\*\s*"(.*?)"', text)
    if match:
        return match.group(1).strip()
    return ""


def extract_section(text: str, pattern: str, flags = 0) -> str:
    """
    정규식 패턴으로 섹션 추출
    
    Args:
        text: 전체 텍스트
        pattern: 정규식 패턴
        flags: 정규식 플래그
    
    Returns:
        str: 추출된 섹션 텍스트
    """
    match = re.search(pattern, text, flags)
    if match:
        return match.group(1).strip()
    return ""


def validate_parsing_result(result: Dict[str, Any]) -> bool:
    """
    파싱 결과 검증
    
    Args:
        result: parse_resume_with_llm의 반환값
    
    Returns:
        bool: 유효한 결과인지 여부
    """
    required_keys = ["ncs_level", "rcs_level", "markdown_content"]
    
    for key in required_keys:
        if key not in result or not result[key]:
            print(f"[Validation Error] 필수 키 '{key}'가 없거나 비어있습니다.")
            return False
    
    # Markdown 최소 길이 검증
    if len(result["markdown_content"]) < 100:
        print(f"[Validation Error] Markdown 출력이 너무 짧습니다.")
        return False
    
    return True
