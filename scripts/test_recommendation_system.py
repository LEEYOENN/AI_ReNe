import sys
import os
import logging
from sqlalchemy.orm import Session

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from core.database import SessionLocal, engine, Base
from models.user import Jobseeker, Company
from models.document import RecruitmentNotice, Resume
from models.recommendation import RecommendationResult
from services.matching_service import MatchingService
from services.simulation_service import SimulationService
from services.auditor_service import AuditorService

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def test_recommendation_system():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        logger.info("=== [Step 1] 1st Stage Matching (Vector Search) ===")
        matching_service = MatchingService(db)
        
        # 1-1. Find Top Notices for Jobseekers
        jobseekers = db.query(Jobseeker).all()
        logger.info(f"Found {len(jobseekers)} Jobseekers.")
        
        jobseeker_matches = {} # {jobseeker_id: [notice_id, ...]}

        for seeker in jobseekers:
            # Check if resume exists
            resume = db.query(Resume).filter(Resume.jobseeker_id == seeker.id).first()
            if not resume:
                logger.info(f"Skipping Jobseeker {seeker.id} (No Resume)")
                continue
                
            logger.info(f"\n[Jobseeker {seeker.id}: {seeker.name}] Finding Top Notices...")
            try:
                top_notices = matching_service.find_top_notices(seeker.id, top_k=2)
                jobseeker_matches[seeker.id] = top_notices
                
                for idx, match in enumerate(top_notices):
                    logger.info(f"  Rank {idx+1}: Notice ID {match['recruitment_notice_id']} (Score: {match['score']:.4f})")
            except Exception as e:
                logger.error(f"  Error: {e}")

        # 1-2. Find Top Candidates for Notices
        notices = db.query(RecruitmentNotice).all()
        logger.info(f"\nFound {len(notices)} Recruitment Notices.")
        
        notice_matches = {} # {notice_id: [jobseeker_id, ...]}

        for notice in notices:
            logger.info(f"\n[Notice {notice.id}] Finding Top Candidates...")
            try:
                top_candidates = matching_service.find_top_candidates(notice.id, top_k=5)
                notice_matches[notice.id] = top_candidates
                
                for idx, match in enumerate(top_candidates):
                    logger.info(f"  Rank {idx+1}: Jobseeker ID {match['jobseeker_id']} (Score: {match['score']:.4f})")
            except Exception as e:
                logger.error(f"  Error: {e}")

        logger.info("\n=== [Step 2] 2nd Stage AI2AI Simulation & Evaluation ===")
        simulation_service = SimulationService(db)
        auditor_service = AuditorService(db)
        
        # Collect all unique pairs to simulate
        pairs_to_simulate = set()

        # 1. From Jobseeker's perspective (Top 2)
        for seeker_id, matches in jobseeker_matches.items():
            for match in matches:
                pairs_to_simulate.add((seeker_id, match['recruitment_notice_id']))

        # 2. From Company's perspective (Top 5)
        for notice_id, matches in notice_matches.items():
            for match in matches:
                pairs_to_simulate.add((match['jobseeker_id'], notice_id))
        
        logger.info(f"Total unique pairs to simulate: {len(pairs_to_simulate)}")

        processed_count = 0
        
        for seeker_id, notice_id in pairs_to_simulate:
            logger.info(f"\n[{processed_count + 1}/{len(pairs_to_simulate)}] Running Simulation: Jobseeker {seeker_id} <-> Notice {notice_id}")
            
            try:
                # Check if already exists to avoid re-running (optional, but good for idempotency)
                existing = db.query(RecommendationResult).filter(
                    RecommendationResult.jobseeker_id == seeker_id,
                    RecommendationResult.recruitment_notice_id == notice_id
                ).first()
                
                if existing:
                    logger.info("  Skipping: Already evaluated.")
                    processed_count += 1
                    continue

                # Run Simulation
                transcript = simulation_service.run_simulation(seeker_id, notice_id)
                logger.info(f"  Simulation Completed. Transcript Length: {len(transcript)} chars")
                
                # Run Evaluation
                result = auditor_service.evaluate_and_save(seeker_id, notice_id, transcript)
                logger.info(f"  Evaluation Completed. Score: {result.total_score}, Recommended: {result.is_recommended}")
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"  Simulation/Evaluation Failed: {e}")

        logger.info("\n=== [Step 3] Final Report (Top Recommendations) ===")
        # Print Top 2 Companies for Jobseeker (based on Step 1 matching for now, as Step 2 is expensive)
        # But user asked for "Top 2 recommended companies... to check SWOT".
        # SWOT is only available if Step 2 is run.
        # Since we only ran Step 2 for 1 pair, we can only show SWOT for that pair.
        # I will print the SWOT for the processed pair(s).
        
        results = db.query(RecommendationResult).all()
        for res in results:
            logger.info(f"\n[Recommendation Result] Jobseeker {res.jobseeker_id} -> Notice {res.recruitment_notice_id}")
            logger.info(f"  Total Score: {res.total_score}")
            logger.info(f"  Details: {res.score_details}")
            logger.info(f"  SWOT Analysis: {res.swot_analysis}")
            logger.info(f"  Summary: {res.summary}")

    finally:
        db.close()

if __name__ == "__main__":
    test_recommendation_system()
