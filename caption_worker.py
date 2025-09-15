# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Caption Generation Background Worker

This is a standalone service that processes queued caption generation tasks.
It runs independently of the web application and continuously monitors for new tasks.

Usage:
    python3 caption_worker.py [--log-level INFO] [--check-interval 5]
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
from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
from models import CaptionGenerationTask, TaskStatus

logger = logging.getLogger(__name__)

class CaptionWorker:
    """Standalone background worker for processing caption generation tasks"""
    
    def __init__(self, check_interval: float = 5.0):
        self.config = Config()
        self.db_manager = DatabaseManager(self.config)
        self.caption_service = WebCaptionGenerationService(self.db_manager)
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
        logger.info("Starting Caption Generation Background Worker")
        logger.info(f"Check interval: {self.check_interval} seconds")
        
        self.setup_signal_handlers()
        self.running = True
        
        try:
            await self.run_worker_loop()
        except Exception as e:
            logger.error(f"Fatal error in worker: {e}")
            raise
        finally:
            logger.info("Caption Generation Background Worker stopped")
    
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
                    await self.process_task(task)
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
    
    async def process_task(self, task: CaptionGenerationTask):
        """Process a single task"""
        try:
            # Use the caption service to process the task
            await self.caption_service._process_task(task)
            self.stats['tasks_processed'] += 1
            logger.info(f"Successfully processed task {task.id}")
            
        except Exception as e:
            logger.error(f"Error processing task {task.id}: {e}")
            self.stats['tasks_failed'] += 1
            
            # Mark task as failed
            try:
                with self.db_manager.get_session() as session:
                    db_task = session.query(CaptionGenerationTask)\
                        .filter(CaptionGenerationTask.id == task.id)\
                        .first()
                    
                    if db_task:
                        db_task.status = TaskStatus.FAILED
                        db_task.error_message = str(e)
                        db_task.completed_at = datetime.now()
                        session.commit()
                        
            except Exception as db_error:
                logger.error(f"Error updating failed task status: {db_error}")
    
    def print_stats(self):
        """Print worker statistics"""
        uptime = datetime.now() - self.stats['start_time']
        logger.info("=== Worker Statistics ===")
        logger.info(f"Uptime: {uptime}")
        logger.info(f"Tasks processed: {self.stats['tasks_processed']}")
        logger.info(f"Tasks failed: {self.stats['tasks_failed']}")
        logger.info(f"Last check: {self.stats['last_check']}")
        logger.info("========================")

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Caption Generation Background Worker')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                        default='INFO', help='Set logging level')
    parser.add_argument('--check-interval', type=float, default=5.0,
                        help='Interval between task checks in seconds (default: 5.0)')
    parser.add_argument('--stats', action='store_true',
                        help='Show current task statistics and exit')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/caption_worker.log')
        ]
    )
    
    if args.stats:
        # Show current task statistics
        config = Config()
        db_manager = DatabaseManager(config)
        
        with db_manager.get_session() as session:
            queued_count = session.query(CaptionGenerationTask).filter(CaptionGenerationTask.status == TaskStatus.QUEUED).count()
            running_count = session.query(CaptionGenerationTask).filter(CaptionGenerationTask.status == TaskStatus.RUNNING).count()
            completed_count = session.query(CaptionGenerationTask).filter(CaptionGenerationTask.status == TaskStatus.COMPLETED).count()
            failed_count = session.query(CaptionGenerationTask).filter(CaptionGenerationTask.status == TaskStatus.FAILED).count()
            
            print("Task Status Summary:")
            print(f"  Queued: {queued_count}")
            print(f"  Running: {running_count}")
            print(f"  Completed: {completed_count}")
            print(f"  Failed: {failed_count}")
        
        return
    
    # Create and start worker
    worker = CaptionWorker(check_interval=args.check_interval)
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        worker.print_stats()

if __name__ == "__main__":
    asyncio.run(main())