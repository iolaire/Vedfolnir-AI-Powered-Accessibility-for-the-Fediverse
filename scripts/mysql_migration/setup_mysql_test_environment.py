#!/usr/bin/env python3
"""
MySQL Test Environment Setup Script

Sets up MySQL test environment including test database, user, and permissions.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MySQLTestEnvironmentSetup:
    """Setup MySQL test environment"""
    
    def __init__(self, config_override: Dict[str, Any] = None):
        """Initialize MySQL test environment setup"""
        self.config = {
            'host': 'localhost',
            'port': 3306,
            'root_user': 'database_user_1d7b0d0696a20',
            'root_password': 'EQA&bok7',
            'test_user': 'database_user_1d7b0d0696a20',
            'test_password': 'EQA&bok7',
            'test_database': 'vedfolnir_test',
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
        
        if config_override:
            self.config.update(config_override)
        
        # Load from environment
        self._load_from_environment()
    
    def _load_from_environment(self):
        """Load configuration from environment variables"""
        env_mapping = {
            'host': 'MYSQL_TEST_HOST',
            'port': 'MYSQL_TEST_PORT',
            'root_user': 'MYSQL_ROOT_USER',
            'root_password': 'MYSQL_ROOT_PASSWORD',
            'test_user': 'MYSQL_TEST_USER',
            'test_password': 'MYSQL_TEST_PASSWORD',
            'test_database': 'MYSQL_TEST_DATABASE',
        }
        
        for key, env_var in env_mapping.items():
            if os.getenv(env_var):
                if key == 'port':
                    self.config[key] = int(os.getenv(env_var))
                else:
                    self.config[key] = os.getenv(env_var)
    
    def check_mysql_server(self) -> bool:
        """Check if MySQL server is running and accessible"""
        logger.info("Checking MySQL server availability...")
        
        try:
            import pymysql
            
            # Try to connect to MySQL server
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['root_user'],
                password=self.config['root_password'],
                charset=self.config['charset']
            )
            
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                logger.info(f"✅ MySQL server is running: {version}")
            
            connection.close()
            return True
            
        except ImportError:
            logger.error("❌ PyMySQL not installed. Install with: pip install pymysql")
            return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to MySQL server: {e}")
            logger.info("Make sure MySQL server is running and credentials are correct")
            return False
    
    def create_test_user(self) -> bool:
        """Create MySQL test user with appropriate permissions"""
        logger.info(f"Creating MySQL test user: {self.config['test_user']}")
        
        try:
            import pymysql
            
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['root_user'],
                password=self.config['root_password'],
                charset=self.config['charset']
            )
            
            with connection.cursor() as cursor:
                # Create user if not exists
                cursor.execute(f"""
                    CREATE USER IF NOT EXISTS '{self.config['test_user']}'@'%' 
                    IDENTIFIED BY '{self.config['test_password']}'
                """)
                
                # Grant permissions for test databases
                cursor.execute(f"""
                    GRANT ALL PRIVILEGES ON `{self.config['test_database']}%`.* 
                    TO '{self.config['test_user']}'@'%'
                """)
                
                # Grant permissions to create and drop test databases
                cursor.execute(f"""
                    GRANT CREATE, DROP ON *.* TO '{self.config['test_user']}'@'%'
                """)
                
                # Flush privileges
                cursor.execute("FLUSH PRIVILEGES")
                
                connection.commit()
            
            connection.close()
            logger.info(f"✅ Test user created: {self.config['test_user']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create test user: {e}")
            return False
    
    def create_base_test_database(self) -> bool:
        """Create base test database"""
        logger.info(f"Creating base test database: {self.config['test_database']}")
        
        try:
            import pymysql
            
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['root_user'],
                password=self.config['root_password'],
                charset=self.config['charset']
            )
            
            with connection.cursor() as cursor:
                # Create base test database
                cursor.execute(f"""
                    CREATE DATABASE IF NOT EXISTS `{self.config['test_database']}` 
                    CHARACTER SET {self.config['charset']} 
                    COLLATE {self.config['collation']}
                """)
                
                connection.commit()
            
            connection.close()
            logger.info(f"✅ Base test database created: {self.config['test_database']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create base test database: {e}")
            return False
    
    def test_user_permissions(self) -> bool:
        """Test that the test user has correct permissions"""
        logger.info("Testing test user permissions...")
        
        try:
            import pymysql
            
            # Connect as test user
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['test_user'],
                password=self.config['test_password'],
                charset=self.config['charset']
            )
            
            test_db_name = f"{self.config['test_database']}_permission_test"
            
            with connection.cursor() as cursor:
                # Test database creation
                cursor.execute(f"""
                    CREATE DATABASE IF NOT EXISTS `{test_db_name}` 
                    CHARACTER SET {self.config['charset']} 
                    COLLATE {self.config['collation']}
                """)
                
                # Test table creation
                cursor.execute(f"USE `{test_db_name}`")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS test_table (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(100) NOT NULL
                    ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """)
                
                # Test data operations
                cursor.execute("INSERT INTO test_table (name) VALUES ('test')")
                cursor.execute("SELECT * FROM test_table")
                result = cursor.fetchall()
                
                # Clean up test database
                cursor.execute(f"DROP DATABASE `{test_db_name}`")
                
                connection.commit()
            
            connection.close()
            
            if result:
                logger.info("✅ Test user permissions verified")
                return True
            else:
                logger.error("❌ Test user permissions verification failed")
                return False
            
        except Exception as e:
            logger.error(f"❌ Test user permissions test failed: {e}")
            return False
    
    def create_test_environment_config(self) -> bool:
        """Create test environment configuration file"""
        logger.info("Creating test environment configuration...")
        
        project_root = Path(__file__).parent.parent.parent
        config_file = project_root / 'tests' / 'mysql_test_env.py'
        
        config_content = f'''#!/usr/bin/env python3
"""
MySQL Test Environment Configuration

Auto-generated configuration for MySQL test environment.
"""

import os

# MySQL Test Configuration
MYSQL_TEST_CONFIG = {{
    'host': '{self.config['host']}',
    'port': {self.config['port']},
    'user': '{self.config['test_user']}',
    'password': '{self.config['test_password']}',
    'base_database': '{self.config['test_database']}',
    'charset': '{self.config['charset']}',
    'collation': '{self.config['collation']}'
}}

# Environment variables for test configuration
TEST_ENV_VARS = {{
    'MYSQL_TEST_HOST': '{self.config['host']}',
    'MYSQL_TEST_PORT': '{self.config['port']}',
    'MYSQL_TEST_USER': '{self.config['test_user']}',
    'MYSQL_TEST_PASSWORD': '{self.config['test_password']}',
    'MYSQL_TEST_DATABASE': '{self.config['test_database']}',
}}

def setup_test_environment():
    """Set up test environment variables"""
    for key, value in TEST_ENV_VARS.items():
        os.environ.setdefault(key, str(value))

def get_test_database_url(database_name: str = None) -> str:
    """Get MySQL test database URL"""
    db_name = database_name or MYSQL_TEST_CONFIG['base_database']
    return (
        f"mysql+pymysql://"
        f"{{MYSQL_TEST_CONFIG['user']}}:{{MYSQL_TEST_CONFIG['password']}}@"
        f"{{MYSQL_TEST_CONFIG['host']}}:{{MYSQL_TEST_CONFIG['port']}}/"
        f"{{db_name}}?charset={{MYSQL_TEST_CONFIG['charset']}}"
    )

if __name__ == "__main__":
    setup_test_environment()
    print("MySQL test environment configured")
'''
        
        try:
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            logger.info(f"✅ Test environment config created: {config_file}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create test environment config: {e}")
            return False
    
    def install_dependencies(self) -> bool:
        """Install required Python dependencies for MySQL testing"""
        logger.info("Installing MySQL testing dependencies...")
        
        dependencies = [
            'pymysql',
            'cryptography',  # Required for MySQL authentication
        ]
        
        try:
            for dep in dependencies:
                logger.info(f"Installing {dep}...")
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', dep
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            logger.info("✅ MySQL testing dependencies installed")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to install dependencies: {e}")
            return False
    
    def setup_complete_environment(self) -> bool:
        """Set up complete MySQL test environment"""
        logger.info("=== Setting up MySQL Test Environment ===")
        
        steps = [
            ("Installing dependencies", self.install_dependencies),
            ("Checking MySQL server", self.check_mysql_server),
            ("Creating test user", self.create_test_user),
            ("Creating base test database", self.create_base_test_database),
            ("Testing user permissions", self.test_user_permissions),
            ("Creating test environment config", self.create_test_environment_config),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Step: {step_name}")
            if not step_func():
                logger.error(f"❌ Failed at step: {step_name}")
                return False
        
        logger.info("✅ MySQL test environment setup completed successfully!")
        return True
    
    def generate_setup_report(self) -> str:
        """Generate setup report"""
        report = [
            "=== MySQL Test Environment Setup Report ===",
            "",
            "CONFIGURATION:",
            f"Host: {self.config['host']}:{self.config['port']}",
            f"Test User: {self.config['test_user']}",
            f"Test Database: {self.config['test_database']}",
            f"Charset: {self.config['charset']}",
            f"Collation: {self.config['collation']}",
            "",
            "SETUP RESULTS:",
            "✅ MySQL server accessible",
            f"✅ Test user '{self.config['test_user']}' created with permissions",
            f"✅ Base test database '{self.config['test_database']}' created",
            "✅ User permissions verified",
            "✅ Test environment configuration created",
            "",
            "USAGE:",
            "1. Run tests with: python -m pytest tests/",
            "2. Individual test: python tests/test_example.py",
            "3. Clean test databases: python scripts/mysql_migration/cleanup_test_databases.py",
            "",
            "ENVIRONMENT VARIABLES:",
            f"MYSQL_TEST_HOST={self.config['host']}",
            f"MYSQL_TEST_PORT={self.config['port']}",
            f"MYSQL_TEST_USER={self.config['test_user']}",
            f"MYSQL_TEST_PASSWORD={self.config['test_password']}",
            f"MYSQL_TEST_DATABASE={self.config['test_database']}",
        ]
        
        return "\n".join(report)


def main():
    """Main setup function"""
    logger.info("MySQL Test Environment Setup")
    
    # Check for configuration overrides
    config_override = {}
    
    # Prompt for root password if not set
    if not os.getenv('MYSQL_ROOT_PASSWORD'):
        import getpass
        root_password = getpass.getpass("MySQL root password (press Enter if no password): ")
        if root_password:
            config_override['root_password'] = root_password
    
    # Initialize setup
    setup = MySQLTestEnvironmentSetup(config_override)
    
    # Perform setup
    success = setup.setup_complete_environment()
    
    # Generate report
    report = setup.generate_setup_report()
    
    # Save report
    project_root = Path(__file__).parent.parent.parent
    report_path = project_root / 'scripts' / 'mysql_migration' / 'mysql_test_environment_setup_report.txt'
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    logger.info(f"Setup report saved to: {report_path}")
    
    if success:
        logger.info("✅ MySQL test environment setup completed successfully!")
        print("\n" + "="*60)
        print("MySQL Test Environment Ready!")
        print("="*60)
        print(f"Test User: {setup.config['test_user']}")
        print(f"Test Database: {setup.config['test_database']}")
        print(f"Configuration: tests/mysql_test_env.py")
        print("="*60)
        return True
    else:
        logger.error("❌ MySQL test environment setup failed!")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
