#!/usr/bin/env python3
"""
MySQL Model Optimization Validation Script

Validates that all SQLAlchemy models have been properly optimized for MySQL.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MySQLModelValidator:
    """Validates MySQL model optimizations"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.validation_results = []
        self.issues = []
    
    def test_mysql_table_args(self) -> bool:
        """Test that all models use enhanced MySQL table args"""
        logger.info("Testing MySQL table args configuration...")
        
        try:
            sys.path.append(str(self.project_root))
            from models import mysql_table_args
            
            # Check enhanced MySQL table args
            required_args = {
                'mysql_engine': 'InnoDB',
                'mysql_charset': 'utf8mb4',
                'mysql_collate': 'utf8mb4_unicode_ci'
            }
            
            for key, expected_value in required_args.items():
                if key not in mysql_table_args:
                    self.issues.append(f"Missing MySQL table arg: {key}")
                    return False
                elif mysql_table_args[key] != expected_value:
                    self.issues.append(f"Incorrect MySQL table arg {key}: {mysql_table_args[key]} != {expected_value}")
                    return False
            
            logger.info("✅ MySQL table args are properly configured")
            return True
            
        except Exception as e:
            self.issues.append(f"MySQL table args test failed: {e}")
            return False
    
    def test_foreign_key_constraints(self) -> bool:
        """Test that all foreign keys have proper ON DELETE clauses"""
        logger.info("Testing foreign key constraints...")
        
        try:
            sys.path.append(str(self.project_root))
            from models import Base, Post, Image, PlatformConnection, ProcessingRun, CaptionGenerationTask, CaptionGenerationUserSettings
            
            models_to_check = [Post, Image, PlatformConnection, ProcessingRun, CaptionGenerationTask, CaptionGenerationUserSettings]
            
            for model in models_to_check:
                model_name = model.__name__
                
                # Check foreign key constraints
                for fk in model.__table__.foreign_keys:
                    if not fk.ondelete:
                        self.issues.append(f"{model_name}: Foreign key {fk.column.name} missing ON DELETE clause")
                        return False
                    elif fk.ondelete.upper() not in ['CASCADE', 'SET NULL', 'RESTRICT']:
                        self.issues.append(f"{model_name}: Foreign key {fk.column.name} has invalid ON DELETE: {fk.ondelete}")
                        return False
            
            logger.info("✅ All foreign key constraints are properly configured")
            return True
            
        except Exception as e:
            self.issues.append(f"Foreign key constraints test failed: {e}")
            return False
    
    def test_data_type_optimization(self) -> bool:
        """Test that data types are optimized for MySQL"""
        logger.info("Testing data type optimization...")
        
        try:
            sys.path.append(str(self.project_root))
            from models import Base, Post, Image, User, PlatformConnection
            
            models_to_check = [Post, Image, User, PlatformConnection]
            
            for model in models_to_check:
                model_name = model.__name__
                
                for column_name, column in model.__table__.columns.items():
                    # Check for overly long VARCHAR columns that should be TEXT
                    if hasattr(column.type, 'length') and column.type.length and column.type.length > 500:
                        # Allow specific exceptions for URLs and paths
                        if column_name not in ['instance_url', 'local_path', 'post_url']:
                            self.issues.append(f"{model_name}.{column_name}: VARCHAR({column.type.length}) should be TEXT")
                            return False
                    
                    # Check that URLs use TEXT type
                    if 'url' in column_name.lower() and column_name != 'instance_url':
                        if not str(column.type).upper().startswith('TEXT'):
                            # image_url should be TEXT, others can be VARCHAR with reasonable length
                            if column_name == 'image_url':
                                self.issues.append(f"{model_name}.{column_name}: Should use TEXT type for long URLs")
                                return False
            
            logger.info("✅ Data types are properly optimized for MySQL")
            return True
            
        except Exception as e:
            self.issues.append(f"Data type optimization test failed: {e}")
            return False
    
    def test_index_optimization(self) -> bool:
        """Test that models have proper indexes for MySQL"""
        logger.info("Testing index optimization...")
        
        try:
            sys.path.append(str(self.project_root))
            from models import Base, Post, Image, User, PlatformConnection, ProcessingRun, CaptionGenerationTask
            
            # Expected indexes for each model
            expected_indexes = {
                'User': ['ix_user_email_active', 'ix_user_username_active', 'ix_user_role_active'],
                'Post': ['ix_post_platform_created', 'ix_post_created_at', 'ix_post_platform_type'],
                'Image': ['ix_image_post_attachment', 'ix_image_platform_status', 'ix_image_status_created'],
                'PlatformConnection': ['ix_platform_user_active', 'ix_platform_type_active', 'ix_platform_user_default'],
                'ProcessingRun': ['ix_processing_run_user_started', 'ix_processing_run_platform_status'],
                'CaptionGenerationTask': ['ix_caption_task_user_status', 'ix_caption_task_platform_status'],
            }
            
            models_to_check = {
                'User': User,
                'Post': Post, 
                'Image': Image,
                'PlatformConnection': PlatformConnection,
                'ProcessingRun': ProcessingRun,
                'CaptionGenerationTask': CaptionGenerationTask,
            }
            
            for model_name, model in models_to_check.items():
                if model_name in expected_indexes:
                    table_indexes = {idx.name for idx in model.__table__.indexes if idx.name}
                    
                    for expected_index in expected_indexes[model_name]:
                        if expected_index not in table_indexes:
                            self.issues.append(f"{model_name}: Missing expected index {expected_index}")
                            return False
            
            logger.info("✅ Index optimization is properly configured")
            return True
            
        except Exception as e:
            self.issues.append(f"Index optimization test failed: {e}")
            return False
    
    def test_unique_constraints(self) -> bool:
        """Test that models have proper unique constraints"""
        logger.info("Testing unique constraints...")
        
        try:
            sys.path.append(str(self.project_root))
            from models import Base, Post, Image, PlatformConnection, CaptionGenerationUserSettings
            
            # Expected unique constraints
            expected_constraints = {
                'Post': ['uq_post_platform'],
                'Image': ['uq_image_platform', 'uq_post_attachment'],
                'PlatformConnection': ['uq_user_platform_name', 'uq_user_instance_username'],
                'CaptionGenerationUserSettings': ['uq_user_platform_settings'],
            }
            
            models_to_check = {
                'Post': Post,
                'Image': Image,
                'PlatformConnection': PlatformConnection,
                'CaptionGenerationUserSettings': CaptionGenerationUserSettings,
            }
            
            for model_name, model in models_to_check.items():
                if model_name in expected_constraints:
                    table_constraints = {uc.name for uc in model.__table__.constraints if hasattr(uc, 'name') and uc.name}
                    
                    for expected_constraint in expected_constraints[model_name]:
                        if expected_constraint not in table_constraints:
                            self.issues.append(f"{model_name}: Missing expected unique constraint {expected_constraint}")
                            return False
            
            logger.info("✅ Unique constraints are properly configured")
            return True
            
        except Exception as e:
            self.issues.append(f"Unique constraints test failed: {e}")
            return False
    
    def test_enum_usage(self) -> bool:
        """Test that models use SQLAlchemy ENUMs properly"""
        logger.info("Testing ENUM usage...")
        
        try:
            sys.path.append(str(self.project_root))
            from models import User, Image, ProcessingRun, CaptionGenerationTask, UserRole, ProcessingStatus, TaskStatus
            from sqlalchemy import Enum as SQLEnum
            
            # Check that enum columns use SQLEnum
            enum_columns = [
                (User, 'role', UserRole),
                (Image, 'status', ProcessingStatus),
                (CaptionGenerationTask, 'status', TaskStatus),
            ]
            
            for model, column_name, enum_class in enum_columns:
                column = getattr(model, column_name)
                if not isinstance(column.type, SQLEnum):
                    self.issues.append(f"{model.__name__}.{column_name}: Should use SQLEnum type")
                    return False
            
            logger.info("✅ ENUM usage is properly configured")
            return True
            
        except Exception as e:
            self.issues.append(f"ENUM usage test failed: {e}")
            return False
    
    def test_relationship_loading(self) -> bool:
        """Test that relationships use proper loading strategies"""
        logger.info("Testing relationship loading strategies...")
        
        try:
            sys.path.append(str(self.project_root))
            from models import User, PlatformConnection
            
            # Check that relationships use select loading
            user_relationships = ['platform_connections', 'sessions']
            platform_relationships = ['user', 'posts', 'images', 'processing_runs', 'user_sessions']
            
            for rel_name in user_relationships:
                if hasattr(User, rel_name):
                    rel = getattr(User, rel_name)
                    if hasattr(rel.property, 'lazy') and rel.property.lazy != 'select':
                        self.issues.append(f"User.{rel_name}: Should use lazy='select' loading")
                        return False
            
            for rel_name in platform_relationships:
                if hasattr(PlatformConnection, rel_name):
                    rel = getattr(PlatformConnection, rel_name)
                    if hasattr(rel.property, 'lazy') and rel.property.lazy != 'select':
                        self.issues.append(f"PlatformConnection.{rel_name}: Should use lazy='select' loading")
                        return False
            
            logger.info("✅ Relationship loading strategies are properly configured")
            return True
            
        except Exception as e:
            self.issues.append(f"Relationship loading test failed: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all MySQL model optimization validation tests"""
        logger.info("=== MySQL Model Optimization Validation ===")
        
        tests = {
            'mysql_table_args': self.test_mysql_table_args(),
            'foreign_key_constraints': self.test_foreign_key_constraints(),
            'data_type_optimization': self.test_data_type_optimization(),
            'index_optimization': self.test_index_optimization(),
            'unique_constraints': self.test_unique_constraints(),
            'enum_usage': self.test_enum_usage(),
            'relationship_loading': self.test_relationship_loading(),
        }
        
        return tests
    
    def generate_report(self, test_results: Dict[str, bool]) -> str:
        """Generate validation report"""
        passed = sum(test_results.values())
        total = len(test_results)
        
        report = [
            "=== MySQL Model Optimization Validation Report ===",
            f"Tests passed: {passed}/{total}",
            f"Issues found: {len(self.issues)}",
            ""
        ]
        
        # Test results
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            report.append(f"{status}: {test_name.replace('_', ' ').title()}")
        
        report.append("")
        
        # Issues
        if self.issues:
            report.extend([
                "🚨 ISSUES FOUND:",
                ""
            ])
            for issue in self.issues:
                report.append(f"  - {issue}")
        else:
            report.extend([
                "✅ SUCCESS: All MySQL model optimizations validated!",
                "Models are properly optimized for MySQL performance and features.",
            ])
        
        return "\n".join(report)


def main():
    """Main validation function"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info(f"Validating MySQL model optimization in: {project_root}")
    
    validator = MySQLModelValidator(project_root)
    test_results = validator.run_all_tests()
    
    # Generate report
    report = validator.generate_report(test_results)
    
    # Save report
    report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'mysql_model_validation_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Print summary
    passed = sum(test_results.values())
    total = len(test_results)
    
    logger.info(f"Validation completed: {passed}/{total} tests passed")
    logger.info(f"Issues found: {len(validator.issues)}")
    logger.info(f"Report saved to: {report_path}")
    
    if passed == total and len(validator.issues) == 0:
        logger.info("✅ SUCCESS: MySQL model optimization validation passed!")
        return True
    else:
        logger.error("❌ FAILURE: MySQL model optimization validation failed!")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
