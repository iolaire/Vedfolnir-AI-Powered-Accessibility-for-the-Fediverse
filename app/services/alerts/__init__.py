# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Consolidated Alert Framework

This module provides the unified alert system for the Vedfolnir application.
All alert-related functionality is centralized here to ensure single-framework governance.
"""

from .components.alert_manager import AlertManager, AlertThresholds, NotificationChannel, NotificationConfig
from .components.alert_threshold_validator import AlertThresholdValidator, ValidationResult, ValidationSeverity
from .components.rate_limiting_configuration_adapter import RateLimitingConfigurationAdapter

__all__ = [
    'AlertManager',
    'AlertThresholds', 
    'NotificationChannel',
    'NotificationConfig',
    'AlertThresholdValidator',
    'ValidationResult',
    'ValidationSeverity',
    'RateLimitingConfigurationAdapter'
]