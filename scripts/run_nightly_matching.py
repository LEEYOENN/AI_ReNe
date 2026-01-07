import sys
import os
import logging
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from core.database import SessionLocal
from models.document import RecruitmentNotice
from services.matching_service import MatchingService
from services.simulation_service import SimulationService
from services.auditor_service import AuditorService

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("data/logs/nightly_matching.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_nightly_matching():
    logger.info("=== Starting Nightly Matching Batch Job ===")
    db: Session = SessionLocal()
    
    try:
        # Initialize Services
        matching_service = MatchingService(db)
        simulation_service = SimulationService(db)
        auditor_service = AuditorService(db)

        # 1. Fetch Active Recruitment Notices
        # In a real scenario, we might filter by 'is_active' or 'created_at'
        notices = db.query(RecruitmentNotice).all()
        logger.info(f"Found {len(notices)} recruitment notices.")

        for notice in notices:
            logger.info(f"Processing Notice ID: {notice.id}")
            
            try:
                # 2. Find Top Candidates (Vector Search)
                candidates = matching_service.find_top_candidates(notice.id, top_k=5)
                logger.info(f"  Found {len(candidates)} candidates for Notice {notice.id}")

                for cand in candidates:
                    jobseeker_id = cand['jobseeker_id']
                    logger.info(f"    Simulating Interview for Jobseeker {jobseeker_id}...")
                    
                    try:
                        # 3. Run AI2AI Simulation
                        transcript = simulation_service.run_simulation(jobseeker_id, notice.id)
                        
                        # 4. Evaluate & Save
                        result = auditor_service.evaluate_and_save(jobseeker_id, notice.id, transcript)
                        
                        status = "RECOMMENDED" if result.is_recommended else "NOT RECOMMENDED"
                        logger.info(f"    Result: {status} (Score: {result.total_score})")
                        
                    except Exception as e:
                        logger.error(f"    Error processing Jobseeker {jobseeker_id}: {e}")
                        continue # Skip to next candidate

            except Exception as e:
                logger.error(f"  Error processing Notice {notice.id}: {e}")
                continue # Skip to next notice

    except Exception as e:
        logger.critical(f"Critical Batch Job Error: {e}")
    finally:
        db.close()
        logger.info("=== Nightly Matching Batch Job Finished ===")

if __name__ == "__main__":
    run_nightly_matching()
