# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Compliance and Audit Framework

This module provides comprehensive compliance and audit capabilities including:
- Audit logging for all system events
- GDPR compliance features
- Immutable audit logs
- Automated compliance reporting
- Data lifecycle management
"""

from .audit_logger import AuditLogger, AuditEvent, AuditEventType
from .gdpr_compliance import GDPRComplianceService
from .compliance_reporter import ComplianceReporter
from .data_lifecycle_manager import DataLifecycleManager

__all__ = [
    'AuditLogger',
    'AuditEvent', 
    'AuditEventType',
    'GDPRComplianceService',
    'ComplianceReporter',
    'DataLifecycleManager'
]