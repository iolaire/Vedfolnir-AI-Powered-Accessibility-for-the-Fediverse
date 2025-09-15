# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Manual Task Processor

This script manually processes queued caption generation tasks.
Use this when the background processor isn't running or to process specific tasks.
"""

import asyncio
import sys
import argparse
from config import Config
from app.core.database.core.database_manager import DatabaseManager
from app.utils.processing.web_caption_generation_service import WebCaptionGenerationService
from models import CaptionGenerationTask, TaskStatus

async def process_queued_tasks(limit=10):
    """Process queued caption generation tasks"""
    print("Starting manual task processor...")
    
    config = Config()
    db_manager = DatabaseManager(config)
    caption_service = WebCaptionGenerationService(db_manager)
    
    # Get queued tasks
    with db_manager.get_session() as session:
        queued_tasks = session.query(CaptionGenerationTask)\
            .filter(CaptionGenerationTask.status == TaskStatus.QUEUED)\
            .order_by(CaptionGenerationTask.created_at.asc())\
            .limit(limit)\
            .all()
        
        if not queued_tasks:
            print("No queued tasks found.")
            return
        
        print(f"Found {len(queued_tasks)} queued tasks:")
        for task in queued_tasks:
            print(f"  - Task {task.id} (User {task.user_id}, Platform {task.platform_connection_id})")
    
    # Process each task
    processed_count = 0
    for task in queued_tasks:
        try:
            print(f"\nProcessing task {task.id}...")
            await caption_service._process_task(task)
            processed_count += 1
            print(f"✅ Task {task.id} processed successfully")
        except Exception as e:
            print(f"❌ Error processing task {task.id}: {e}")
    
    print(f"\nProcessed {processed_count}/{len(queued_tasks)} tasks successfully.")

async def process_specific_task(task_id):
    """Process a specific task by ID"""
    print(f"Processing specific task: {task_id}")
    
    config = Config()
    db_manager = DatabaseManager(config)
    caption_service = WebCaptionGenerationService(db_manager)
    
    # Get the specific task
    with db_manager.get_session() as session:
        task = session.query(CaptionGenerationTask)\
            .filter(CaptionGenerationTask.id == task_id)\
            .first()
        
        if not task:
            print(f"Task {task_id} not found.")
            return
        
        if task.status != TaskStatus.QUEUED:
            print(f"Task {task_id} is not queued (status: {task.status}). Cannot process.")
            return
        
        print(f"Found task {task.id} (User {task.user_id}, Platform {task.platform_connection_id})")
    
    # Process the task
    try:
        print(f"Processing task {task.id}...")
        await caption_service._process_task(task)
        print(f"✅ Task {task.id} processed successfully")
    except Exception as e:
        print(f"❌ Error processing task {task.id}: {e}")

def show_task_status():
    """Show current task status"""
    config = Config()
    db_manager = DatabaseManager(config)
    
    with db_manager.get_session() as session:
        # Get task counts by status
        queued_count = session.query(CaptionGenerationTask).filter(CaptionGenerationTask.status == TaskStatus.QUEUED).count()
        running_count = session.query(CaptionGenerationTask).filter(CaptionGenerationTask.status == TaskStatus.RUNNING).count()
        completed_count = session.query(CaptionGenerationTask).filter(CaptionGenerationTask.status == TaskStatus.COMPLETED).count()
        failed_count = session.query(CaptionGenerationTask).filter(CaptionGenerationTask.status == TaskStatus.FAILED).count()
        cancelled_count = session.query(CaptionGenerationTask).filter(CaptionGenerationTask.status == TaskStatus.CANCELLED).count()
        
        print("Task Status Summary:")
        print(f"  Queued: {queued_count}")
        print(f"  Running: {running_count}")
        print(f"  Completed: {completed_count}")
        print(f"  Failed: {failed_count}")
        print(f"  Cancelled: {cancelled_count}")
        
        # Show recent queued tasks
        if queued_count > 0:
            print("\nQueued Tasks:")
            queued_tasks = session.query(CaptionGenerationTask)\
                .filter(CaptionGenerationTask.status == TaskStatus.QUEUED)\
                .order_by(CaptionGenerationTask.created_at.asc())\
                .limit(10)\
                .all()
            
            for task in queued_tasks:
                print(f"  - {task.id} (User {task.user_id}, Created: {task.created_at})")

async def main():
    parser = argparse.ArgumentParser(description='Process queued caption generation tasks')
    parser.add_argument('--task-id', help='Process a specific task by ID')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of tasks to process (default: 10)')
    parser.add_argument('--status', action='store_true', help='Show task status and exit')
    
    args = parser.parse_args()
    
    if args.status:
        show_task_status()
        return
    
    if args.task_id:
        await process_specific_task(args.task_id)
    else:
        await process_queued_tasks(args.limit)

if __name__ == "__main__":
    asyncio.run(main())