#!/usr/bin/env python3
"""
Manual Task Processor for Stuck Caption Generation Tasks
"""

import sys
import asyncio
from datetime import datetime, timezone

# Add the current directory to Python path
sys.path.append('.')

from web_app import app
from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
from app.core.database.core.database_manager import DatabaseManager
from models import CaptionGenerationTask, TaskStatus

async def process_stuck_task(task_id: str):
    """Process a specific stuck task"""
    
    with app.app_context():
        # Initialize database manager
        from config import Config
        config = Config()
        db_manager = DatabaseManager(config)
        
        # Initialize caption service
        caption_service = WebCaptionGenerationService(db_manager)
        
        # Get the task
        with db_manager.get_session() as session:
            task = session.query(CaptionGenerationTask).filter_by(id=task_id).first()
            
            if not task:
                print(f"Task {task_id} not found")
                return
                
            print(f"Found task: {task.id}")
            print(f"Status: {task.status}")
            print(f"User ID: {task.user_id}")
            print(f"Platform Connection ID: {task.platform_connection_id}")
            print(f"Created: {task.created_at}")
            
            if task.status != TaskStatus.QUEUED:
                print(f"Task is not in QUEUED status (current: {task.status})")
                return
                
            # Update task to RUNNING
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            task.current_step = "Starting caption generation"
            task.progress_percent = 0
            session.commit()
            
            print("Updated task status to RUNNING")
            
            try:
                # Process the task
                print("Starting caption generation process...")
                
                # Get task settings
                settings = task.settings_json or {}
                
                # Start the actual caption generation
                await caption_service._process_task(task)
                
                print("Caption generation completed successfully!")
                
            except Exception as e:
                print(f"Error processing task: {e}")
                # Update task to FAILED
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.now(timezone.utc)
                session.commit()
                raise

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_stuck_task.py <task_id>")
        sys.exit(1)
        
    task_id = sys.argv[1]
    print(f"Processing stuck task: {task_id}")
    
    asyncio.run(process_stuck_task(task_id))
