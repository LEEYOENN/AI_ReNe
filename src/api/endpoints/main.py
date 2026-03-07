from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from core.database import engine, Base
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "./")))
from rene_interview import rene_router
from p2p_interview_api import p2p_router
from auth import auth_router
import company_ai_interview_api
from upload_api import upload_router
from jobseeker_profile_api import profile_router
from view_router import view_router
from recommendation_api import recommendation_router
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

def init_db():
    print("DB 초기화 스크립트 실행...")
    # Base.metadata.drop_all(bind=engine) # 기존 거 싹 지우고 다시 만들려면 주석 해제
    Base.metadata.create_all(bind=engine) # DB 생성
    print("모든 테이블이 생성되었습니다.")

# 서버 시작 시 무조건 실행될 수 있도록 lifespan 설정
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버 켜질 때 실행
    init_db()
    yield

app = FastAPI(title="ReNe Project API", version="1.0.0", lifespan=lifespan)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(p2p_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(company_ai_interview_api.router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(recommendation_router, prefix="/api/v1", tags=["Recommendation"])
app.include_router(view_router)

# Static files mount
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# [Data 폴더 마운트] 외부에서 HTML 파일 접근 허용
data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../data"))

# /data 경로로 들어오는 요청은 data 폴더의 파일을 보여줌
if os.path.exists(data_dir):
    app.mount("/data", StaticFiles(directory=data_dir), name="data")

if __name__ == "__main__":
    init_db()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

