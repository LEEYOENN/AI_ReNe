from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from api.deps import get_db

router = APIRouter(prefix="/jobseeker/ai-interview", tags=["Jobseeker AI Interview"])