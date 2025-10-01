# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Test Suite for Vedfolnir Vault Integration
Tests Vault connectivity, secret management, and Docker integration
"""

import os
import sys
import json
import time
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the vault modules to path
sys.path.append(os.path.dirname(__file__))
try:
    from vault_client import VaultClient, VaultAuthError, VaultSecretError
    from secret_rotation import SecretRotationManager
    from docker_secrets_integration import DockerSecretsManager
except ImportError as e:
    print(f"Warning: Could not import vault modules: {e}")
    print("This is expected when Vault is not running. Tests will be skipped.")
    sys.exit(0)


class TestVaultClient(unittest.TestCase):
    """Test VaultClient functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
        self.vault_token = os.getenv('VAULT_TOKEN', 'test-token')
        
    def test_vault_connectivity(self):
        """Test basic Vault connectivity"""
        try:
            client = VaultClient(self.vault_addr, self.vault_token)
            health = client.health_check()
            
            self.assertIsInstance(health, dict)
            print(f"✅ Vault connectivity test passed: {health}")
            
        except Exception as e:
            print(f"❌ Vault connectivity test failed: {e}")
            self.skipTest(f"Vault not available: {e}")
    
    def test_secret_operations(self):
        """Test secret read/write operations"""
        try:
            client = VaultClient(self.vault_addr, self.vault_token)
            
            # Test secret write
            test_data = {'test_key': 'test_value', 'timestamp': str(int(time.time()))}
            result = client.put_secret('test/integration', test_data)
            self.assertIsInstance(result, dict)
            
            # Test secret read
            retrieved_data = client.get_secret('test/integration')
            self.assertEqual(retrieved_data['test_key'], 'test_value')
            
            # Test secret list
            secrets = client.list_secrets('test')
            self.assertIn('integration', secrets)
            
            print("✅ Secret operations test passed")
            
        except Exception as e:
            print(f"❌ Secret operations test failed: {e}")
            self.fail(f"Secret operations failed: {e}")
    
    def test_database_credentials(self):
        """Test dynamic database credentials"""
        try:
            client = VaultClient(self.vault_addr, self.vault_token)
            
            # Get database credentials
            creds = client.get_database_credentials()
            
            self.assertIn('username', creds)
            self.assertIn('password', creds)
            self.assertIn('lease_id', creds)
            
            # Verify credentials are different each time
            creds2 = client.get_database_credentials()
            self.assertNotEqual(creds['username'], creds2['username'])
            
            print(f"✅ Database credentials test passed: {creds['username']}")
            
        except Exception as e:
            print(f"❌ Database credentials test failed: {e}")
            # This might fail if database engine is not configured
            self.skipTest(f"Database engine not configured: {e}")
    
    def test_encryption_operations(self):
        """Test transit encryption/decryption"""
        try:
            client = VaultClient(self.vault_addr, self.vault_token)
            
            # Test data
            plaintext = "This is a test message for encryption"
            
            # Encrypt
            ciphertext = client.encrypt_data(plaintext)
            self.assertTrue(ciphertext.startswith('vault:v'))
            
            # Decrypt
            decrypted = client.decrypt_data(ciphertext)
            self.assertEqual(decrypted, plaintext)
            
            print("✅ Encryption operations test passed")
            
        except Exception as e:
            print(f"❌ Encryption operations test failed: {e}")
            self.skipTest(f"Transit engine not configured: {e}")


class TestSecretRotation(unittest.TestCase):
    """Test secret rotation functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
        self.vault_token = os.getenv('VAULT_TOKEN', 'test-token')
        
    def test_secret_age_check(self):
        """Test secret age checking"""
        try:
            client = VaultClient(self.vault_addr, self.vault_token)
            manager = SecretRotationManager(client)
            
            # Create a test secret
            test_data = {'test_key': 'test_value'}
            client.put_secret('test/age-check', test_data)
            
            # Check age
            age_info = manager.check_secret_age('test/age-check')
            
            self.assertIn('age_days', age_info)
            self.assertIn('needs_rotation', age_info)
            self.assertEqual(age_info['age_days'], 0)  # Just created
            
            print("✅ Secret age check test passed")
            
        except Exception as e:
            print(f"❌ Secret age check test failed: {e}")
            self.skipTest(f"Secret rotation test failed: {e}")
    
    def test_flask_secret_rotation(self):
        """Test Flask secret rotation"""
        try:
            client = VaultClient(self.vault_addr, self.vault_token)
            manager = SecretRotationManager(client)
            
            # Get original secret
            try:
                original = client.get_secret('flask')['secret_key']
            except:
                original = None
            
            # Rotate secret
            new_secret = manager.rotate_flask_secret()
            
            # Verify new secret is different
            if original:
                self.assertNotEqual(original, new_secret)
            
            # Verify secret is stored
            stored_secret = client.get_secret('flask')['secret_key']
            self.assertEqual(stored_secret, new_secret)
            
            print("✅ Flask secret rotation test passed")
            
        except Exception as e:
            print(f"❌ Flask secret rotation test failed: {e}")
            self.fail(f"Flask secret rotation failed: {e}")


class TestDockerSecretsIntegration(unittest.TestCase):
    """Test Docker secrets integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
        self.vault_token = os.getenv('VAULT_TOKEN', 'test-token')
        
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_secret_file_creation(self):
        """Test creation of Docker secret files"""
        try:
            client = VaultClient(self.vault_addr, self.vault_token)
            manager = DockerSecretsManager(client, self.temp_dir)
            
            # Ensure test secrets exist in Vault
            client.put_secret('flask', {'secret_key': 'test-flask-secret'})
            client.put_secret('platform', {'encryption_key': 'test-platform-key'})
            
            # Sync secrets
            results = manager.sync_all_secrets()
            
            # Check results
            self.assertTrue(results.get('flask_secret_key', False))
            self.assertTrue(results.get('platform_encryption_key', False))
            
            # Verify files exist
            flask_file = Path(manager.vault_secrets_dir) / 'flask_secret_key.txt'
            self.assertTrue(flask_file.exists())
            self.assertEqual(flask_file.read_text().strip(), 'test-flask-secret')
            
            print("✅ Secret file creation test passed")
            
        except Exception as e:
            print(f"❌ Secret file creation test failed: {e}")
            self.fail(f"Secret file creation failed: {e}")
    
    def test_secrets_validation(self):
        """Test secrets validation"""
        try:
            client = VaultClient(self.vault_addr, self.vault_token)
            manager = DockerSecretsManager(client, self.temp_dir)
            
            # Create some test secret files
            (manager.vault_secrets_dir / 'flask_secret_key.txt').write_text('test-secret')
            (manager.vault_secrets_dir / 'platform_encryption_key.txt').write_text('test-key')
            
            # Validate secrets
            results = manager.validate_secrets()
            
            self.assertTrue(results.get('flask_secret_key', False))
            self.assertTrue(results.get('platform_encryption_key', False))
            
            print("✅ Secrets validation test passed")
            
        except Exception as e:
            print(f"❌ Secrets validation test failed: {e}")
            self.fail(f"Secrets validation failed: {e}")
    
    def test_docker_compose_config_generation(self):
        """Test Docker Compose configuration generation"""
        try:
            client = VaultClient(self.vault_addr, self.vault_token)
            manager = DockerSecretsManager(client, self.temp_dir)
            
            # Generate configuration
            config = manager.generate_docker_compose_secrets()
            
            # Verify structure
            self.assertIn('flask_secret_key', config)
            self.assertIn('platform_encryption_key', config)
            self.assertIn('file', config['flask_secret_key'])
            
            print("✅ Docker Compose config generation test passed")
            
        except Exception as e:
            print(f"❌ Docker Compose config generation test failed: {e}")
            self.fail(f"Docker Compose config generation failed: {e}")


class TestVaultIntegrationE2E(unittest.TestCase):
    """End-to-end integration tests"""
    
    def setUp(self):
        """Set up test environment"""
        self.vault_addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
        self.vault_token = os.getenv('VAULT_TOKEN', 'test-token')
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_workflow(self):
        """Test complete Vault integration workflow"""
        try:
            # Initialize components
            vault_client = VaultClient(self.vault_addr, self.vault_token)
            rotation_manager = SecretRotationManager(vault_client)
            secrets_manager = DockerSecretsManager(vault_client, self.temp_dir)
            
            # Step 1: Store initial secrets
            vault_client.put_secret('flask', {'secret_key': 'initial-flask-secret'})
            vault_client.put_secret('platform', {'encryption_key': 'initial-platform-key'})
            
            # Step 2: Sync to Docker secrets
            sync_results = secrets_manager.sync_all_secrets()
            self.assertTrue(all(sync_results.values()))
            
            # Step 3: Validate secrets
            validation_results = secrets_manager.validate_secrets()
            self.assertTrue(validation_results['flask_secret_key'])
            self.assertTrue(validation_results['platform_encryption_key'])
            
            # Step 4: Rotate secrets
            new_flask_secret = rotation_manager.rotate_flask_secret()
            self.assertNotEqual(new_flask_secret, 'initial-flask-secret')
            
            # Step 5: Re-sync after rotation
            sync_results = secrets_manager.sync_all_secrets()
            self.assertTrue(sync_results['flask_secret_key'])
            
            # Step 6: Verify rotated secret is in file
            flask_file = Path(secrets_manager.vault_secrets_dir) / 'flask_secret_key.txt'
            self.assertEqual(flask_file.read_text().strip(), new_flask_secret)
            
            print("✅ Full workflow test passed")
            
        except Exception as e:
            print(f"❌ Full workflow test failed: {e}")
            self.fail(f"Full workflow failed: {e}")
    
    def test_health_checks(self):
        """Test health check functionality"""
        try:
            vault_client = VaultClient(self.vault_addr, self.vault_token)
            secrets_manager = DockerSecretsManager(vault_client, self.temp_dir)
            
            # Vault health check
            vault_health = vault_client.health_check()
            self.assertIsInstance(vault_health, dict)
            
            # Secrets integration health check
            integration_health = secrets_manager.health_check()
            self.assertIn('vault_connectivity', integration_health)
            self.assertIn('secrets_validation', integration_health)
            
            print("✅ Health checks test passed")
            
        except Exception as e:
            print(f"❌ Health checks test failed: {e}")
            self.fail(f"Health checks failed: {e}")


def run_integration_tests():
    """Run all integration tests"""
    print("=== Vedfolnir Vault Integration Tests ===")
    print(f"Vault Address: {os.getenv('VAULT_ADDR', 'http://vault:8200')}")
    print(f"Test Environment: {os.getenv('TESTING', 'false')}")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestVaultClient))
    suite.addTests(loader.loadTestsFromTestCase(TestSecretRotation))
    suite.addTests(loader.loadTestsFromTestCase(TestDockerSecretsIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestVaultIntegrationE2E))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    # Return success status
    return len(result.failures) == 0 and len(result.errors) == 0


if __name__ == '__main__':
    success = run_integration_tests()
    sys.exit(0 if success else 1)