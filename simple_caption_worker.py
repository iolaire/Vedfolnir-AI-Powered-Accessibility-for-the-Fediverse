# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Simple Caption Generation Worker

A simplified worker that bypasses the complex TaskGroup initialization
and processes tasks more directly.
"""

import asyncio
import signal
import sys
import argparse
import logging
from datetime import datetime
from typing import Optional

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from models import CaptionGenerationTask, TaskStatus

logger = logging.getLogger(__name__)

class SimpleCaptionWorker:
    """Simplified caption worker that avoids TaskGroup issues"""
    
    def __init__(self, check_interval: float = 5.0):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.check_interval = check_interval
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Statistics
        self.stats = {
            'tasks_processed': 0,
            'tasks_failed': 0,
            'start_time': datetime.now(),
            'last_check': None
        }
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the background worker"""
        logger.info("Starting Simple Caption Generation Worker")
        logger.info(f"Check interval: {self.check_interval} seconds")
        
        self.setup_signal_handlers()
        self.running = True
        
        try:
            await self.run_worker_loop()
        except Exception as e:
            logger.error(f"Fatal error in worker: {e}")
            raise
        finally:
            logger.info("Simple Caption Generation Worker stopped")
    
    async def run_worker_loop(self):
        """Main worker loop"""
        logger.info("Worker loop started")
        
        while not self.shutdown_event.is_set():
            try:
                self.stats['last_check'] = datetime.now()
                
                # Get next queued task
                task = self.get_next_queued_task()
                
                if task:
                    logger.info(f"Processing task {task.id} for user {task.user_id}")
                    await self.process_task_simple(task)
                else:
                    # No tasks available, wait before checking again
                    try:
                        await asyncio.wait_for(
                            self.shutdown_event.wait(), 
                            timeout=self.check_interval
                        )
                    except asyncio.TimeoutError:
                        # Timeout is expected, continue loop
                        pass
                        
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                # Wait a bit before retrying to avoid tight error loops
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), 
                        timeout=min(self.check_interval, 10.0)
                    )
                except asyncio.TimeoutError:
                    pass
    
    def get_next_queued_task(self) -> Optional[CaptionGenerationTask]:
        """Get the next queued task from the database"""
        try:
            with self.db_manager.get_session() as session:
                task = session.query(CaptionGenerationTask)\
                    .filter(CaptionGenerationTask.status == TaskStatus.QUEUED)\
                    .order_by(CaptionGenerationTask.created_at.asc())\
                    .first()
                
                if task:
                    # Detach from session to avoid issues
                    session.expunge(task)
                    return task
                    
        except Exception as e:
            logger.error(f"Error getting next task: {e}")
        
        return None
    
    async def process_task_simple(self, task: CaptionGenerationTask):
        """Process a single task using the main.py approach"""
        try:
            # Mark task as running
            self.mark_task_running(task.id)
            logger.info(f"Starting processing for task {task.id}")
            
            # Use the main.py approach to process the user
            from main import Vedfolnir
            
            # Get user info
            with self.db_manager.get_session() as session:
                from models import User
                user = session.query(User).filter_by(id=task.user_id).first()
                if not user:
                    raise Exception(f"User {task.user_id} not found")
                
                username = user.username
                logger.info(f"Processing task {task.id} for user '{username}' (ID: {task.user_id})")
            
            # Create Vedfolnir instance and process
            logger.info(f"Creating Vedfolnir instance for task {task.id}")
            bot = Vedfolnir(self.config, reprocess_all=False)
            
            logger.info(f"Running caption generation for user '{username}' (task {task.id})")
            await bot.run_multi_user([username], skip_ollama=False)
            
            # Mark task as completed
            success_message = f"Successfully processed user '{username}' via main.py approach"
            self.mark_task_completed(task.id, success_message)
            self.stats['tasks_processed'] += 1
            logger.info(f"✅ Task {task.id} completed successfully")
            
        except Exception as e:
            error_msg = f"Failed to process task {task.id}: {str(e)}"
            logger.error(error_msg)
            logger.exception("Full exception details:")
            self.stats['tasks_failed'] += 1
            
            # Mark task as failed
            self.mark_task_failed(task.id, str(e))
    
    def mark_task_running(self, task_id: str):
        """Mark task as running"""
        try:
            with self.db_manager.get_session() as session:
                task = session.query(CaptionGenerationTask)\
                    .filter(CaptionGenerationTask.id == task_id)\
                    .first()
                
                if task:
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Error marking task as running: {e}")
    
    def mark_task_completed(self, task_id: str, message: str = None):
        """Mark task as completed"""
        try:
            with self.db_manager.get_session() as session:
                task = session.query(CaptionGenerationTask)\
                    .filter(CaptionGenerationTask.id == task_id)\
                    .first()
                
                if task:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                    task.progress_percent = 100
                    task.current_step = "Completed"
                    # Don't store success messages in error_message field
                    # Clear any previous error message on successful completion
                    task.error_message = None
                    if message:
                        # Store success message in admin_notes field instead
                        task.admin_notes = message
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Error marking task as completed: {e}")
    
    def mark_task_failed(self, task_id: str, error_message: str):
        """Mark task as failed"""
        try:
            with self.db_manager.get_session() as session:
                task = session.query(CaptionGenerationTask)\
                    .filter(CaptionGenerationTask.id == task_id)\
                    .first()
                
                if task:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    task.error_message = error_message
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Error marking task as failed: {e}")
    
    def print_stats(self):
        """Print worker statistics"""
        uptime = datetime.now() - self.stats['start_time']
        logger.info("=== Worker Statistics ===")
        logger.info(f"Uptime: {uptime}")
        logger.info(f"Tasks processed: {self.stats['tasks_processed']}")
        logger.info(f"Tasks failed: {self.stats['tasks_failed']}")
        logger.info(f"Last check: {self.stats['last_check']}")
        logger.info("========================")
    
    def get_task_status(self, task_id: str) -> dict:
        """Get detailed status of a specific task"""
        try:
            with self.db_manager.get_session() as session:
                task = session.query(CaptionGenerationTask)\
                    .filter(CaptionGenerationTask.id == task_id)\
                    .first()
                
                if not task:
                    return {"error": f"Task {task_id} not found"}
                
                return {
                    "id": task.id,
                    "status": task.status.value if task.status else None,
                    "user_id": task.user_id,
                    "progress_percent": task.progress_percent,
                    "current_step": task.current_step,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "error_message": task.error_message,
                    "admin_notes": task.admin_notes,
                    "retry_count": task.retry_count
                }
                
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return {"error": str(e)}

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Simple Caption Generation Worker')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                        default='INFO', help='Set logging level')
    parser.add_argument('--check-interval', type=float, default=5.0,
                        help='Interval between task checks in seconds (default: 5.0)')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/simple_caption_worker.log')
        ]
    )
    
    # Create and start worker
    worker = SimpleCaptionWorker(check_interval=args.check_interval)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        worker.print_stats()

if __name__ == "__main__":
    asyncio.run(main())