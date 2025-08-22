#!/usr/bin/env python3
"""
MySQL Model Optimization Script

Analyzes and optimizes SQLAlchemy models for MySQL-specific features and performance.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Any

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MySQLModelOptimizer:
    """Optimizes SQLAlchemy models for MySQL performance and features"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.optimizations_applied = []
        self.recommendations = []
        
        # MySQL-specific optimizations to apply
        self.mysql_optimizations = {
            'data_types': {
                'String(500)': 'String(500)',  # Keep reasonable for indexes
                'String(1000)': 'Text',  # Convert long strings to TEXT
                'Text': 'Text',  # Already optimal
                'Integer': 'Integer',  # Already optimal
                'Boolean': 'Boolean',  # Already optimal
                'DateTime': 'DateTime',  # Already optimal
            },
            'indexes': {
                'email': 'UNIQUE INDEX',
                'username': 'UNIQUE INDEX', 
                'created_at': 'INDEX',
                'updated_at': 'INDEX',
                'platform_type': 'INDEX',
                'instance_url': 'INDEX',
                'status': 'INDEX',
                'is_active': 'INDEX',
                'user_id': 'INDEX',
                'platform_connection_id': 'INDEX',
            },
            'constraints': {
                'foreign_keys': 'ON DELETE CASCADE',
                'unique_constraints': 'UNIQUE',
            }
        }
    
    def analyze_current_models(self) -> Dict[str, Any]:
        """Analyze current model definitions for MySQL optimization opportunities"""
        logger.info("Analyzing current SQLAlchemy models...")
        
        models_file = self.project_root / 'models.py'
        if not models_file.exists():
            raise FileNotFoundError("models.py not found")
        
        with open(models_file, 'r') as f:
            content = f.read()
        
        analysis = {
            'mysql_table_args_usage': 'mysql_table_args' in content,
            'innodb_engine_specified': 'mysql_engine.*InnoDB' in content,
            'utf8mb4_charset': 'utf8mb4' in content,
            'foreign_key_constraints': 'ForeignKey' in content,
            'indexes_defined': 'Index(' in content or 'index=True' in content,
            'unique_constraints': 'UniqueConstraint' in content,
            'enum_usage': 'SQLEnum' in content,
            'relationship_loading': 'lazy=' in content,
        }
        
        return analysis
    
    def generate_mysql_optimized_models(self) -> str:
        """Generate MySQL-optimized model enhancements"""
        logger.info("Generating MySQL-optimized model enhancements...")
        
        optimizations = []
        
        # Enhanced MySQL table arguments
        optimizations.append("""
# Enhanced MySQL-specific table options for optimal performance
mysql_table_args = {
    'mysql_engine': 'InnoDB',
    'mysql_charset': 'utf8mb4',
    'mysql_collate': 'utf8mb4_unicode_ci',
    'mysql_row_format': 'DYNAMIC',  # Better for variable-length columns
}

# MySQL-specific index options for better performance
mysql_index_args = {
    'mysql_length': {'text_columns': 255},  # Limit index length for TEXT columns
    'mysql_using': 'BTREE',  # Explicit B-tree indexes
}
""")
        
        # Enhanced User model optimizations
        optimizations.append("""
# Enhanced User model with MySQL optimizations
class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        # Composite indexes for common query patterns
        Index('ix_user_email_active', 'email', 'is_active'),
        Index('ix_user_username_active', 'username', 'is_active'),
        Index('ix_user_role_active', 'role', 'is_active'),
        Index('ix_user_created_login', 'created_at', 'last_login'),
        Index('ix_user_verification_status', 'email_verified', 'is_active'),
        
        # MySQL-specific table options
        mysql_table_args
    )
    
    # Optimized column definitions for MySQL
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)  # Optimal length for indexes
    email = Column(String(255), unique=True, nullable=False)    # Standard email length
    password_hash = Column(String(255), nullable=False)         # Standard bcrypt length
    
    # Use ENUM for better performance and data integrity
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Optimized timestamp columns
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
""")
        
        # Enhanced Post model optimizations
        optimizations.append("""
# Enhanced Post model with MySQL optimizations
class Post(Base):
    __tablename__ = 'posts'
    __table_args__ = (
        # Composite indexes for efficient queries
        Index('ix_post_platform_created', 'platform_connection_id', 'created_at'),
        Index('ix_post_user_platform', 'user_id', 'platform_connection_id'),
        Index('ix_post_status_created', 'created_at'),  # For chronological queries
        Index('ix_post_platform_type_url', 'platform_type', 'instance_url'),
        
        # Unique constraints with proper naming
        UniqueConstraint('post_id', 'platform_connection_id', name='uq_post_platform'),
        
        # MySQL-specific optimizations
        mysql_table_args
    )
    
    # Optimized column definitions
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(String(255), nullable=False)  # Reduced from 500 for better indexing
    user_id = Column(String(255), nullable=False)  # Consistent with platform limits
    post_url = Column(Text, nullable=False)        # URLs can be very long
    post_content = Column(Text, nullable=True)     # Content can be large
    
    # Optimized timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Foreign key with proper constraints
    platform_connection_id = Column(
        Integer, 
        ForeignKey('platform_connections.id', ondelete='CASCADE'), 
        nullable=False
    )
""")
        
        # Enhanced Image model optimizations
        optimizations.append("""
# Enhanced Image model with MySQL optimizations
class Image(Base):
    __tablename__ = 'images'
    __table_args__ = (
        # Composite indexes for efficient queries
        Index('ix_image_post_attachment', 'post_id', 'attachment_index'),
        Index('ix_image_platform_status', 'platform_connection_id', 'status'),
        Index('ix_image_status_created', 'status', 'created_at'),
        Index('ix_image_category_status', 'image_category', 'status'),
        Index('ix_image_quality_score', 'caption_quality_score'),
        
        # Unique constraints
        UniqueConstraint('image_post_id', 'platform_connection_id', name='uq_image_platform'),
        UniqueConstraint('post_id', 'attachment_index', name='uq_post_attachment'),
        
        # MySQL-specific optimizations
        mysql_table_args
    )
    
    # Optimized column definitions
    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    
    # URLs and paths - use TEXT for potentially long values
    image_url = Column(Text, nullable=False)
    local_path = Column(String(500), nullable=False)  # File paths have OS limits
    
    # Metadata with appropriate lengths
    original_filename = Column(String(255), nullable=True)  # Standard filename limit
    media_type = Column(String(100), nullable=True)         # MIME type length
    image_post_id = Column(String(255), nullable=True)      # Platform-specific ID
    
    # Optimized integer columns
    attachment_index = Column(Integer, nullable=False, default=0)
    caption_quality_score = Column(Integer, nullable=True)  # 0-100 score
    
    # Status enum for data integrity
    status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False)
    
    # Optimized text columns
    original_caption = Column(Text, nullable=True)
    generated_caption = Column(Text, nullable=True)
    reviewed_caption = Column(Text, nullable=True)
    final_caption = Column(Text, nullable=True)
    
    # Classification and processing
    image_category = Column(String(100), nullable=True)  # Reasonable category length
    prompt_used = Column(Text, nullable=True)            # Prompts can be long
    
    # Optimized timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    posted_at = Column(DateTime, nullable=True)
""")
        
        # Enhanced PlatformConnection model optimizations
        optimizations.append("""
# Enhanced PlatformConnection model with MySQL optimizations
class PlatformConnection(Base):
    __tablename__ = 'platform_connections'
    __table_args__ = (
        # Composite indexes for efficient platform queries
        Index('ix_platform_user_active', 'user_id', 'is_active'),
        Index('ix_platform_type_instance', 'platform_type', 'instance_url'),
        Index('ix_platform_user_default', 'user_id', 'is_default'),
        Index('ix_platform_last_used', 'last_used'),
        
        # Unique constraints for data integrity
        UniqueConstraint('user_id', 'name', name='uq_user_platform_name'),
        UniqueConstraint('user_id', 'instance_url', 'username', name='uq_user_instance_username'),
        
        # MySQL-specific optimizations
        mysql_table_args
    )
    
    # Optimized column definitions
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Platform identification with appropriate lengths
    name = Column(String(100), nullable=False)           # User-friendly name
    platform_type = Column(String(50), nullable=False)  # 'pixelfed', 'mastodon', etc.
    instance_url = Column(String(500), nullable=False)  # Full URL
    username = Column(String(255), nullable=True)       # Platform username
    
    # Encrypted credentials - use TEXT for encrypted data
    _access_token = Column('access_token', Text, nullable=False)
    _client_key = Column('client_key', Text, nullable=True)
    _client_secret = Column('client_secret', Text, nullable=True)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Optimized timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_used = Column(DateTime, nullable=True)
""")
        
        return "\n".join(optimizations)
    
    def generate_mysql_performance_recommendations(self) -> List[str]:
        """Generate MySQL performance recommendations"""
        recommendations = [
            "MySQL Model Performance Recommendations:",
            "",
            "1. INDEX OPTIMIZATION:",
            "   - Use composite indexes for multi-column WHERE clauses",
            "   - Limit index key length to 767 bytes (191 chars for utf8mb4)",
            "   - Use covering indexes for frequently accessed columns",
            "   - Consider partial indexes for large text columns",
            "",
            "2. DATA TYPE OPTIMIZATION:",
            "   - Use VARCHAR(255) instead of VARCHAR(500+) for indexed columns",
            "   - Use TEXT for large content that doesn't need indexing",
            "   - Use ENUM for fixed sets of values (better than VARCHAR)",
            "   - Use proper integer sizes (TINYINT, SMALLINT, INT, BIGINT)",
            "",
            "3. FOREIGN KEY OPTIMIZATION:",
            "   - Always specify ON DELETE CASCADE/SET NULL for referential integrity",
            "   - Use consistent data types for foreign key relationships",
            "   - Index foreign key columns for join performance",
            "",
            "4. TABLE OPTIMIZATION:",
            "   - Use InnoDB engine for ACID compliance and foreign keys",
            "   - Set ROW_FORMAT=DYNAMIC for variable-length columns",
            "   - Use utf8mb4 charset for full Unicode support",
            "   - Consider partitioning for very large tables",
            "",
            "5. QUERY OPTIMIZATION:",
            "   - Use lazy='select' for relationships to avoid N+1 queries",
            "   - Implement proper pagination for large result sets",
            "   - Use bulk operations for multiple inserts/updates",
            "   - Consider read replicas for read-heavy workloads",
            "",
            "6. MONITORING AND MAINTENANCE:",
            "   - Monitor slow query log for optimization opportunities",
            "   - Use EXPLAIN to analyze query execution plans",
            "   - Regular ANALYZE TABLE to update statistics",
            "   - Monitor index usage and remove unused indexes",
        ]
        
        return recommendations
    
    def validate_mysql_compatibility(self) -> Dict[str, Any]:
        """Validate current models for MySQL compatibility"""
        logger.info("Validating MySQL compatibility...")
        
        try:
            sys.path.append(str(self.project_root))
            from models import Base, User, Post, Image, PlatformConnection
            
            validation_results = {
                'models_found': True,
                'mysql_table_args': True,
                'foreign_keys_present': True,
                'indexes_defined': True,
                'enums_used': True,
                'issues': []
            }
            
            # Check each model for MySQL compatibility
            models_to_check = [User, Post, Image, PlatformConnection]
            
            for model in models_to_check:
                model_name = model.__name__
                
                # Check table args
                if not hasattr(model, '__table_args__'):
                    validation_results['issues'].append(f"{model_name}: Missing __table_args__")
                
                # Check for proper column definitions
                for column_name, column in model.__table__.columns.items():
                    # Check for overly long VARCHAR columns that should be TEXT
                    if hasattr(column.type, 'length') and column.type.length and column.type.length > 500:
                        validation_results['issues'].append(
                            f"{model_name}.{column_name}: VARCHAR({column.type.length}) should be TEXT for MySQL"
                        )
                
                # Check for foreign key constraints
                foreign_keys = [fk for fk in model.__table__.foreign_keys]
                for fk in foreign_keys:
                    if not fk.ondelete:
                        validation_results['issues'].append(
                            f"{model_name}: Foreign key {fk.column.name} missing ON DELETE clause"
                        )
            
            logger.info(f"✅ MySQL compatibility validation completed with {len(validation_results['issues'])} issues")
            return validation_results
            
        except Exception as e:
            logger.error(f"❌ MySQL compatibility validation failed: {e}")
            return {
                'models_found': False,
                'error': str(e),
                'issues': [f"Validation failed: {e}"]
            }
    
    def generate_optimization_report(self) -> str:
        """Generate comprehensive MySQL optimization report"""
        analysis = self.analyze_current_models()
        validation = self.validate_mysql_compatibility()
        recommendations = self.generate_mysql_performance_recommendations()
        
        report = [
            "=== MySQL Model Optimization Report ===",
            "",
            "CURRENT MODEL ANALYSIS:",
            f"✅ MySQL table args usage: {analysis['mysql_table_args_usage']}",
            f"✅ InnoDB engine specified: {analysis['innodb_engine_specified']}",
            f"✅ UTF8MB4 charset: {analysis['utf8mb4_charset']}",
            f"✅ Foreign key constraints: {analysis['foreign_key_constraints']}",
            f"✅ Indexes defined: {analysis['indexes_defined']}",
            f"✅ Unique constraints: {analysis['unique_constraints']}",
            f"✅ Enum usage: {analysis['enum_usage']}",
            f"✅ Relationship loading: {analysis['relationship_loading']}",
            "",
            "MYSQL COMPATIBILITY VALIDATION:",
            f"Models found: {validation.get('models_found', False)}",
            f"Issues found: {len(validation.get('issues', []))}",
            ""
        ]
        
        if validation.get('issues'):
            report.extend([
                "🚨 COMPATIBILITY ISSUES:",
                ""
            ])
            for issue in validation['issues']:
                report.append(f"  - {issue}")
            report.append("")
        
        report.extend([
            "📋 OPTIMIZATION RECOMMENDATIONS:",
            ""
        ])
        report.extend(recommendations)
        
        return "\n".join(report)


def main():
    """Main optimization function"""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    logger.info("Starting MySQL model optimization analysis...")
    logger.info(f"Project root: {project_root}")
    
    optimizer = MySQLModelOptimizer(project_root)
    
    # Generate optimization report
    report = optimizer.generate_optimization_report()
    
    # Save report
    report_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'mysql_model_optimization_report.txt')
    with open(report_path, 'w') as f:
        f.write(report)
    
    # Generate optimized model examples
    optimizations = optimizer.generate_mysql_optimized_models()
    optimizations_path = os.path.join(project_root, 'scripts', 'mysql_migration', 'mysql_optimized_models_examples.py')
    with open(optimizations_path, 'w') as f:
        f.write(optimizations)
    
    logger.info("MySQL model optimization analysis completed")
    logger.info(f"Report saved to: {report_path}")
    logger.info(f"Optimization examples saved to: {optimizations_path}")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
