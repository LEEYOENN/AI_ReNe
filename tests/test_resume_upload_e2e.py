import requests
import webbrowser
import os
import sys
import json
from sqlalchemy import text
from datetime import datetime

# 프로젝트 루트 경로 추가 (모듈 import를 위해)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from src.core.database import SessionLocal
    from src.models.user import Jobseeker
    from src.models.document import Resume
except ImportError as e:
    print(f"Import Error: {e}")
    print("가상환경이 활성화되어 있는지, PYTHONPATH가 올바른지 확인해주세요.")
    sys.exit(1)

# 설정
FILE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "김선재 1 (1).pdf")
API_BASE_URL = "http://localhost:8000"
UPLOAD_URL = f"{API_BASE_URL}/api/v1/upload/jobseeker-docs"
PROFILE_URL = f"{API_BASE_URL}/profile"

def test_upload_and_visualize():
    """
    이력서 업로드 테스트 및 결과 시각화
    1. DB에서 테스트용 Jobseeker 확인 (ID: 1)
    2. PDF 파일 업로드 API 호출
    3. 업로드 결과 확인 (DB Query)
    4. 브라우저로 프로필 페이지 열기
    """
    print("=" * 60)
    print("🚀 이력서 업로드 통합 테스트 시작")
    print("=" * 60)

    # 0. 파일 존재 확인
    if not os.path.exists(FILE_PATH):
        print(f"❌ Error: 파일이 존재하지 않습니다.\n경로: {FILE_PATH}")
        return

    # 1. DB 세션 생성 및 사용자 확인
    db = SessionLocal()
    target_user_id = 1
    
    try:
        user = db.query(Jobseeker).filter(Jobseeker.id == target_user_id).first()
        if not user:
            print(f"⚠️ 경고: ID {target_user_id}인 Jobseeker가 DB에 없습니다.")
            print("   테스트를 위해 임시 사용자를 생성합니다...")
            # 임시 사용자 생성
            new_user = Jobseeker(
                name="김선재",
                email="test_sunjae@example.com",
                password="hashed_password",
                phone="010-1234-5678",
                birthdate=datetime.now(),
                gender="Male",
                address="Seoul",
                verification_badge="SPROUT",
                policy_agree_bool=True
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            target_user_id = new_user.id
            print(f"✅ 임시 사용자 생성 완료 (ID: {target_user_id})")
        else:
            print(f"✅ 테스트 대상 사용자 확인: {user.name} (ID: {user.id})")

    except Exception as e:
        print(f"❌ DB 접속 오류: {e}")
        print("   서버가 실행 중인지, DB 설정이 올바른지 확인해주세요.")
        return
    finally:
        db.close()

    # 2. API 호출
    print(f"\n📡 파일 업로드 요청 전송 중... ({os.path.basename(FILE_PATH)})")
    
    try:
        with open(FILE_PATH, "rb") as f:
            files = {"file": (os.path.basename(FILE_PATH), f, "application/pdf")}
            data = {"jobseeker_id": str(target_user_id), "file_type": "resume"}
            
            response = requests.post(UPLOAD_URL, files=files, data=data)
            
        if response.status_code == 200:
            result = response.json()
            print("\n✅ 업로드 성공!")
            print("-" * 40)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("-" * 40)
            
            # 3. DB 결과 재확인 (Resume 테이블)
            db = SessionLocal()
            resume = db.query(Resume).filter(Resume.jobseeker_id == target_user_id).order_by(Resume.created_at.desc()).first()
            if resume:
                print("\n💾 [DB 확인 Result]")
                print(f"   - Resume ID: {resume.id}")
                print(f"   - NCS Level: {resume.ncs_level}")
                print(f"   - Created At: {resume.created_at}")
                print(f"   - Skills Parsed: {resume.skills}")
            db.close()

            # 4. 브라우저 오픈
            target_url = f"{PROFILE_URL}?user_id={target_user_id}"
            print(f"\n🌐 브라우저를 엽니다: {target_url}")
            webbrowser.open(target_url)
            
        else:
            print(f"\n❌ 업로드 실패 (Status: {response.status_code})")
            print(f"Details: {response.text}")

    except requests.exceptions.ConnectionError:
        print("\n❌ 서버 연결 실패")
        print("   FastAPI 서버가 실행 중인지 확인해주세요. (http://localhost:8000)")

if __name__ == "__main__":
    test_upload_and_visualize()
