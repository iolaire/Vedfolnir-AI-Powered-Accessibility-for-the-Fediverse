# scripts.security.owasp_compliance_validator

OWASP Compliance Validator

Validates application compliance against OWASP Top 10 security standards.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/security/owasp_compliance_validator.py`

## Classes

### OWASPComplianceValidator

```python
class OWASPComplianceValidator
```

OWASP Top 10 compliance validator

**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize OWASP compliance validator

**Type:** Instance method

#### validate_a01_broken_access_control

```python
def validate_a01_broken_access_control(self) -> Dict[str, Any]
```

Validate A01: Broken Access Control

**Type:** Instance method

#### validate_a02_cryptographic_failures

```python
def validate_a02_cryptographic_failures(self) -> Dict[str, Any]
```

Validate A02: Cryptographic Failures

**Type:** Instance method

#### validate_a03_injection

```python
def validate_a03_injection(self) -> Dict[str, Any]
```

Validate A03: Injection

**Type:** Instance method

#### validate_a04_insecure_design

```python
def validate_a04_insecure_design(self) -> Dict[str, Any]
```

Validate A04: Insecure Design

**Type:** Instance method

#### validate_a05_security_misconfiguration

```python
def validate_a05_security_misconfiguration(self) -> Dict[str, Any]
```

Validate A05: Security Misconfiguration

**Type:** Instance method

#### validate_a06_vulnerable_components

```python
def validate_a06_vulnerable_components(self) -> Dict[str, Any]
```

Validate A06: Vulnerable and Outdated Components

**Type:** Instance method

#### validate_a07_identification_authentication_failures

```python
def validate_a07_identification_authentication_failures(self) -> Dict[str, Any]
```

Validate A07: Identification and Authentication Failures

**Type:** Instance method

#### validate_a08_software_data_integrity_failures

```python
def validate_a08_software_data_integrity_failures(self) -> Dict[str, Any]
```

Validate A08: Software and Data Integrity Failures

**Type:** Instance method

#### validate_a09_security_logging_monitoring_failures

```python
def validate_a09_security_logging_monitoring_failures(self) -> Dict[str, Any]
```

Validate A09: Security Logging and Monitoring Failures

**Type:** Instance method

#### validate_a10_server_side_request_forgery

```python
def validate_a10_server_side_request_forgery(self) -> Dict[str, Any]
```

Validate A10: Server-Side Request Forgery (SSRF)

**Type:** Instance method

#### run_full_owasp_compliance_check

```python
def run_full_owasp_compliance_check(self) -> Dict[str, Any]
```

Run full OWASP Top 10 compliance check

**Type:** Instance method

#### _check_authentication_enforcement

```python
def _check_authentication_enforcement(self) -> float
```

**Type:** Instance method

#### _check_authorization_implementation

```python
def _check_authorization_implementation(self) -> float
```

**Type:** Instance method

#### _check_privilege_escalation_prevention

```python
def _check_privilege_escalation_prevention(self) -> float
```

**Type:** Instance method

#### _check_cors_configuration

```python
def _check_cors_configuration(self) -> float
```

**Type:** Instance method

#### _check_data_encryption

```python
def _check_data_encryption(self) -> float
```

**Type:** Instance method

#### _check_secure_protocols

```python
def _check_secure_protocols(self) -> float
```

**Type:** Instance method

#### _check_key_management

```python
def _check_key_management(self) -> float
```

**Type:** Instance method

#### _check_password_hashing

```python
def _check_password_hashing(self) -> float
```

**Type:** Instance method

#### _check_sql_injection_prevention

```python
def _check_sql_injection_prevention(self) -> float
```

**Type:** Instance method

#### _check_xss_prevention

```python
def _check_xss_prevention(self) -> float
```

**Type:** Instance method

#### _check_command_injection_prevention

```python
def _check_command_injection_prevention(self) -> float
```

**Type:** Instance method

#### _check_input_validation

```python
def _check_input_validation(self) -> float
```

**Type:** Instance method

#### _check_threat_modeling

```python
def _check_threat_modeling(self) -> float
```

**Type:** Instance method

#### _check_secure_development

```python
def _check_secure_development(self) -> float
```

**Type:** Instance method

#### _check_security_requirements

```python
def _check_security_requirements(self) -> float
```

**Type:** Instance method

#### _check_defense_in_depth

```python
def _check_defense_in_depth(self) -> float
```

**Type:** Instance method

#### _check_security_headers

```python
def _check_security_headers(self) -> float
```

**Type:** Instance method

#### _check_error_handling

```python
def _check_error_handling(self) -> float
```

**Type:** Instance method

#### _check_default_credentials

```python
def _check_default_credentials(self) -> float
```

**Type:** Instance method

#### _check_unnecessary_features

```python
def _check_unnecessary_features(self) -> float
```

**Type:** Instance method

#### _check_dependency_scanning

```python
def _check_dependency_scanning(self) -> float
```

**Type:** Instance method

#### _check_version_management

```python
def _check_version_management(self) -> float
```

**Type:** Instance method

#### _check_security_updates

```python
def _check_security_updates(self) -> float
```

**Type:** Instance method

#### _check_component_inventory

```python
def _check_component_inventory(self) -> float
```

**Type:** Instance method

#### _check_mfa_implementation

```python
def _check_mfa_implementation(self) -> float
```

**Type:** Instance method

#### _check_session_management

```python
def _check_session_management(self) -> float
```

**Type:** Instance method

#### _check_password_policies

```python
def _check_password_policies(self) -> float
```

**Type:** Instance method

#### _check_brute_force_protection

```python
def _check_brute_force_protection(self) -> float
```

**Type:** Instance method

#### _check_code_signing

```python
def _check_code_signing(self) -> float
```

**Type:** Instance method

#### _check_supply_chain_security

```python
def _check_supply_chain_security(self) -> float
```

**Type:** Instance method

#### _check_integrity_verification

```python
def _check_integrity_verification(self) -> float
```

**Type:** Instance method

#### _check_secure_updates

```python
def _check_secure_updates(self) -> float
```

**Type:** Instance method

#### _check_security_logging

```python
def _check_security_logging(self) -> float
```

**Type:** Instance method

#### _check_log_monitoring

```python
def _check_log_monitoring(self) -> float
```

**Type:** Instance method

#### _check_incident_response

```python
def _check_incident_response(self) -> float
```

**Type:** Instance method

#### _check_alerting_system

```python
def _check_alerting_system(self) -> float
```

**Type:** Instance method

#### _check_url_validation

```python
def _check_url_validation(self) -> float
```

**Type:** Instance method

#### _check_network_segmentation

```python
def _check_network_segmentation(self) -> float
```

**Type:** Instance method

#### _check_whitelist_implementation

```python
def _check_whitelist_implementation(self) -> float
```

**Type:** Instance method

#### _check_response_validation

```python
def _check_response_validation(self) -> float
```

**Type:** Instance method

#### _get_access_control_recommendations

```python
def _get_access_control_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _get_crypto_recommendations

```python
def _get_crypto_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _get_injection_recommendations

```python
def _get_injection_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _get_design_recommendations

```python
def _get_design_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _get_misconfiguration_recommendations

```python
def _get_misconfiguration_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _get_component_recommendations

```python
def _get_component_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _get_auth_recommendations

```python
def _get_auth_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _get_integrity_recommendations

```python
def _get_integrity_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _get_logging_recommendations

```python
def _get_logging_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _get_ssrf_recommendations

```python
def _get_ssrf_recommendations(self, checks: Dict[str, float]) -> List[str]
```

**Type:** Instance method

#### _save_compliance_results

```python
def _save_compliance_results(self, results: Dict[str, Any]) -> None
```

Save compliance results to file

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main validation function

