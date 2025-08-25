// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

/**
 * Configuration Management JavaScript
 * 
 * Handles the admin configuration management interface including:
 * - Loading and displaying configurations
 * - Editing configuration values with validation
 * - Configuration history and rollback
 * - Export/import functionality
 * - Documentation display
 */

let configurationSchema = {};
let currentConfigurations = {};
let currentCategory = 'all';

/**
 * Get CSRF token from meta tag
 */
function getCSRFToken() {
    try {
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (!csrfMeta) {
            console.error('CSRF token not found in page meta tags');
            return null;
        }
        const token = csrfMeta.getAttribute('content');
        if (!token) {
            console.error('CSRF token meta tag found but content is empty');
            return null;
        }
        return token;
    } catch (error) {
        console.error('Error getting CSRF token:', error);
        return null;
    }
}

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    loadConfigurationCategories();
    loadConfigurationSchema();
    loadConfigurations();
    loadRestartRequiredStatus();
    
    // Set up event listeners
    document.getElementById('includeSensitive').addEventListener('change', loadConfigurations);
    
    // Check restart status periodically
    setInterval(loadRestartRequiredStatus, 30000); // Check every 30 seconds
});

/**
 * Load configuration categories
 */
async function loadConfigurationCategories() {
    try {
        const response = await fetch('/admin/api/configuration/categories');
        const data = await response.json();
        
        if (response.ok) {
            const categoryFilters = document.getElementById('categoryFilters');
            
            // Clear existing buttons except "All Categories"
            const allButton = categoryFilters.querySelector('[data-category="all"]');
            categoryFilters.innerHTML = '';
            categoryFilters.appendChild(allButton);
            
            // Add category buttons
            data.categories.forEach(category => {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'btn btn-outline-secondary';
                button.setAttribute('data-category', category.value);
                button.textContent = category.name;
                button.title = category.description;
                button.onclick = () => filterByCategory(category.value);
                categoryFilters.appendChild(button);
            });
            
            // Set up click handler for "All Categories"
            allButton.onclick = () => filterByCategory('all');
        }
    } catch (error) {
        console.error('Error loading configuration categories:', error);
        showAlert('Error loading configuration categories', 'danger');
    }
}

/**
 * Load configuration schema
 */
async function loadConfigurationSchema() {
    try {
        const response = await fetch('/admin/api/configuration/schema');
        const data = await response.json();
        
        if (response.ok) {
            configurationSchema = data.schemas;
        }
    } catch (error) {
        console.error('Error loading configuration schema:', error);
    }
}

/**
 * Load configurations
 */
async function loadConfigurations() {
    try {
        const includeSensitive = document.getElementById('includeSensitive').checked;
        let url = '/admin/api/configuration/';
        
        const params = new URLSearchParams();
        if (currentCategory !== 'all') {
            params.append('category', currentCategory);
        }
        if (includeSensitive) {
            params.append('include_sensitive', 'true');
        }
        
        if (params.toString()) {
            url += '?' + params.toString();
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (response.ok) {
            currentConfigurations = data.configurations;
            displayConfigurations(data.configurations);
        } else {
            showAlert(data.error || 'Error loading configurations', 'danger');
        }
    } catch (error) {
        console.error('Error loading configurations:', error);
        showAlert('Error loading configurations', 'danger');
    }
}

/**
 * Display configurations in the table
 */
function displayConfigurations(configurations) {
    const tbody = document.getElementById('configurationsTableBody');
    tbody.innerHTML = '';
    
    Object.entries(configurations).forEach(([key, value]) => {
        const schema = configurationSchema[key];
        const row = document.createElement('tr');
        
        // Format value for display
        let displayValue = value;
        if (typeof value === 'object') {
            displayValue = JSON.stringify(value);
        } else if (typeof value === 'boolean') {
            displayValue = value ? 'true' : 'false';
        }
        
        // Truncate long values
        if (displayValue && displayValue.length > 50) {
            displayValue = displayValue.substring(0, 50) + '...';
        }
        
        // Check if this configuration requires restart
        const requiresRestart = schema && schema.requires_restart;
        const isPendingRestart = window.pendingRestartConfigs && window.pendingRestartConfigs.includes(key);
        
        // Create status indicators
        let statusIndicators = '';
        if (schema && schema.is_sensitive) {
            statusIndicators += '<i class="bi bi-lock-fill text-warning me-1" title="Sensitive Configuration"></i>';
        }
        if (requiresRestart) {
            statusIndicators += '<i class="bi bi-arrow-clockwise text-info me-1" title="Requires Restart"></i>';
        }
        if (isPendingRestart) {
            statusIndicators += '<span class="badge bg-warning text-dark me-1" title="Restart Required">Restart Required</span>';
        }
        
        row.innerHTML = `
            <td>
                <code>${escapeHtml(key)}</code>
                ${schema && schema.is_sensitive ? '<i class="bi bi-lock-fill text-warning ms-1" title="Sensitive"></i>' : ''}
            </td>
            <td>${escapeHtml(displayValue || 'null')}</td>
            <td>
                <span class="badge bg-secondary">${schema ? schema.category : 'unknown'}</span>
            </td>
            <td>
                <span class="badge bg-info">${schema ? schema.data_type : 'string'}</span>
            </td>
            <td>
                ${statusIndicators || '<span class="text-muted">-</span>'}
            </td>
            <td class="text-muted small">${schema ? escapeHtml(schema.description) : ''}</td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary" onclick="editConfiguration('${key}')" title="Edit Configuration">
                        <i class="bi bi-pencil me-1"></i>Edit
                    </button>
                    <button type="button" class="btn btn-outline-info" onclick="showConfigurationHistory('${key}')" title="View Configuration History">
                        <i class="bi bi-clock-history me-1"></i>History
                    </button>
                </div>
            </td>
        `;
        
        // Add special styling for configurations requiring restart
        if (isPendingRestart) {
            row.classList.add('table-warning');
        }
        
        tbody.appendChild(row);
    });
}

/**
 * Filter configurations by category
 */
function filterByCategory(category) {
    currentCategory = category;
    
    // Update active button
    document.querySelectorAll('#categoryFilters button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-category="${category}"]`).classList.add('active');
    
    // Reload configurations
    loadConfigurations();
}

/**
 * Edit configuration
 */
function editConfiguration(key) {
    const schema = configurationSchema[key];
    const currentValue = currentConfigurations[key];
    
    // Set up modal
    document.getElementById('configKey').value = key;
    document.getElementById('configDescription').textContent = schema ? schema.description : '';
    document.getElementById('configReason').value = '';
    
    // Clear validation messages
    document.getElementById('validationErrors').classList.add('d-none');
    document.getElementById('validationWarnings').classList.add('d-none');
    
    // Create appropriate input based on data type
    const container = document.getElementById('configValueContainer');
    container.innerHTML = '';
    
    let input;
    if (schema) {
        switch (schema.data_type) {
            case 'boolean':
                input = document.createElement('select');
                input.className = 'form-select';
                input.innerHTML = '<option value="true">true</option><option value="false">false</option>';
                input.value = currentValue ? 'true' : 'false';
                break;
            case 'integer':
                input = document.createElement('input');
                input.type = 'number';
                input.className = 'form-control';
                input.value = currentValue || '';
                if (schema.validation_rules) {
                    if (schema.validation_rules.min !== undefined) {
                        input.min = schema.validation_rules.min;
                    }
                    if (schema.validation_rules.max !== undefined) {
                        input.max = schema.validation_rules.max;
                    }
                }
                break;
            case 'float':
                input = document.createElement('input');
                input.type = 'number';
                input.step = 'any';
                input.className = 'form-control';
                input.value = currentValue || '';
                if (schema.validation_rules) {
                    if (schema.validation_rules.min !== undefined) {
                        input.min = schema.validation_rules.min;
                    }
                    if (schema.validation_rules.max !== undefined) {
                        input.max = schema.validation_rules.max;
                    }
                }
                break;
            case 'json':
                input = document.createElement('textarea');
                input.className = 'form-control';
                input.rows = 5;
                input.value = JSON.stringify(currentValue, null, 2);
                break;
            default: // string
                input = document.createElement('input');
                input.type = 'text';
                input.className = 'form-control';
                input.value = currentValue || '';
                break;
        }
    } else {
        // Default to text input
        input = document.createElement('input');
        input.type = 'text';
        input.className = 'form-control';
        input.value = currentValue || '';
    }
    
    input.id = 'configValue';
    container.appendChild(input);
    
    // Add event listeners for validation and impact assessment
    input.addEventListener('input', debounce(() => {
        validateConfigurationValue(key, input.value);
        assessConfigurationImpact(key, input.value);
    }, 500));
    
    // Add blur event for immediate validation
    input.addEventListener('blur', () => {
        validateConfigurationValue(key, input.value);
    });
    
    // Hide impact assessment initially
    document.getElementById('impactAssessment').classList.add('d-none');
    document.getElementById('criticalChangeConfirmation').classList.add('d-none');
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('editConfigModal'));
    modal.show();
}

/**
 * Save configuration
 */
async function saveConfiguration() {
    const key = document.getElementById('configKey').value;
    const valueInput = document.getElementById('configValue');
    const reason = document.getElementById('configReason').value;
    const schema = configurationSchema[key];
    
    // Check for validation errors
    const errorsDiv = document.getElementById('validationErrors');
    if (!errorsDiv.classList.contains('d-none')) {
        showValidationError(['Please fix validation errors before saving.']);
        return;
    }
    
    // Check for critical change confirmation
    const criticalDiv = document.getElementById('criticalChangeConfirmation');
    const confirmCheckbox = document.getElementById('confirmCriticalChange');
    
    if (!criticalDiv.classList.contains('d-none') && !confirmCheckbox.checked) {
        showValidationError(['Please confirm that you understand the risks of this critical configuration change.']);
        return;
    }
    
    let value = valueInput.value;
    
    // Convert value based on data type
    if (schema) {
        try {
            switch (schema.data_type) {
                case 'boolean':
                    value = value === 'true';
                    break;
                case 'integer':
                    value = parseInt(value);
                    break;
                case 'float':
                    value = parseFloat(value);
                    break;
                case 'json':
                    value = JSON.parse(value);
                    break;
                // string remains as is
            }
        } catch (error) {
            showValidationError(['Invalid value format for data type: ' + schema.data_type]);
            return;
        }
    }
    
    try {
        // Get CSRF token - handle both sync and async cases
        let csrfToken = getCSRFToken();
        
        // If it's a Promise, await it
        if (csrfToken && typeof csrfToken.then === 'function') {
            csrfToken = await csrfToken;
        }
        
        if (!csrfToken || typeof csrfToken !== 'string') {
            showAlert('CSRF token not available', 'danger');
            return;
        }
        
        const response = await fetch(`/admin/api/configuration/${key}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                value: value,
                reason: reason
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('editConfigModal'));
            modal.hide();
            
            // Reload configurations and restart status
            loadConfigurations();
            loadRestartRequiredStatus();
            
            // Show success message with restart warning if applicable
            const schema = configurationSchema[key];
            let message = `Configuration ${key} updated successfully`;
            if (schema && schema.requires_restart) {
                message += '. System restart required for changes to take effect.';
            }
            showAlert(message, schema && schema.requires_restart ? 'warning' : 'success');
        } else {
            showAlert(data.error || 'Failed to update configuration', 'danger');
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showAlert('Error saving configuration', 'danger');
    }
}

/**
 * Show configuration history
 */
async function showConfigurationHistory(key) {
    try {
        const response = await fetch(`/admin/api/configuration/${key}/history`);
        const data = await response.json();
        
        if (response.ok) {
            const tbody = document.getElementById('historyTableBody');
            tbody.innerHTML = '';
            
            data.history.forEach(change => {
                const row = document.createElement('tr');
                
                // Format values for display
                let oldValue = change.old_value;
                let newValue = change.new_value;
                
                if (typeof oldValue === 'object') {
                    oldValue = JSON.stringify(oldValue);
                }
                if (typeof newValue === 'object') {
                    newValue = JSON.stringify(newValue);
                }
                
                row.innerHTML = `
                    <td>${new Date(change.changed_at).toLocaleString()}</td>
                    <td>User ${change.changed_by}</td>
                    <td><code>${escapeHtml(oldValue || 'null')}</code></td>
                    <td><code>${escapeHtml(newValue || 'null')}</code></td>
                    <td class="text-muted small">${escapeHtml(change.reason || '')}</td>
                    <td>
                        <button type="button" class="btn btn-sm btn-outline-warning" 
                                onclick="rollbackConfiguration('${key}', '${change.changed_at}')"
                                title="Rollback to this value">
                            <i class="fas fa-undo"></i> Rollback
                        </button>
                    </td>
                `;
                
                tbody.appendChild(row);
            });
            
            // Update modal title
            document.getElementById('historyModalLabel').textContent = `Configuration History: ${key}`;
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('historyModal'));
            modal.show();
        } else {
            showAlert(data.error || 'Error loading configuration history', 'danger');
        }
    } catch (error) {
        console.error('Error loading configuration history:', error);
        showAlert('Error loading configuration history', 'danger');
    }
}

/**
 * Rollback configuration
 */
async function rollbackConfiguration(key, targetTimestamp) {
    if (!confirm(`Are you sure you want to rollback configuration "${key}" to ${new Date(targetTimestamp).toLocaleString()}?`)) {
        return;
    }
    
    const reason = prompt('Please provide a reason for this rollback:');
    if (reason === null) {
        return; // User cancelled
    }
    
    try {
        // Get CSRF token - handle both sync and async cases
        let csrfToken = getCSRFToken();
        
        // If it's a Promise, await it
        if (csrfToken && typeof csrfToken.then === 'function') {
            csrfToken = await csrfToken;
        }
        
        if (!csrfToken || typeof csrfToken !== 'string') {
            showAlert('CSRF token not available', 'danger');
            return;
        }
        
        const response = await fetch(`/admin/api/configuration/${key}/rollback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                target_timestamp: targetTimestamp,
                reason: reason || 'Configuration rollback'
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Close history modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('historyModal'));
            modal.hide();
            
            // Reload configurations
            loadConfigurations();
            
            showAlert(`Configuration ${key} rolled back successfully`, 'success');
        } else {
            showAlert(data.error || 'Failed to rollback configuration', 'danger');
        }
    } catch (error) {
        console.error('Error rolling back configuration:', error);
        showAlert('Error rolling back configuration', 'danger');
    }
}

/**
 * Export configurations
 */
async function exportConfigurations() {
    try {
        const includeSensitive = document.getElementById('includeSensitive').checked;
        let url = '/admin/api/configuration/export';
        
        const params = new URLSearchParams();
        if (currentCategory !== 'all') {
            params.append('category', currentCategory);
        }
        if (includeSensitive) {
            params.append('include_sensitive', 'true');
        }
        
        if (params.toString()) {
            url += '?' + params.toString();
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (response.ok) {
            // Create and download file
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url_obj = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url_obj;
            a.download = `vedfolnir-config-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url_obj);
            
            showAlert('Configurations exported successfully', 'success');
        } else {
            showAlert(data.error || 'Failed to export configurations', 'danger');
        }
    } catch (error) {
        console.error('Error exporting configurations:', error);
        showAlert('Error exporting configurations', 'danger');
    }
}

/**
 * Show import modal
 */
function showImportModal() {
    // Reset form
    document.getElementById('importFile').value = '';
    document.getElementById('validateOnly').checked = false;
    document.getElementById('overwriteExisting').checked = false;
    document.getElementById('importResults').classList.add('d-none');
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('importModal'));
    modal.show();
}

/**
 * Import configurations
 */
async function importConfigurations() {
    const fileInput = document.getElementById('importFile');
    const validateOnly = document.getElementById('validateOnly').checked;
    const overwriteExisting = document.getElementById('overwriteExisting').checked;
    
    if (!fileInput.files[0]) {
        showAlert('Please select a file to import', 'warning');
        return;
    }
    
    try {
        const fileContent = await fileInput.files[0].text();
        const importData = JSON.parse(fileContent);
        
        // Add import options to the data
        importData.validate_only = validateOnly;
        importData.overwrite_existing = overwriteExisting;
        
        // Get CSRF token - handle both sync and async cases
        let csrfToken = getCSRFToken();
        
        // If it's a Promise, await it
        if (csrfToken && typeof csrfToken.then === 'function') {
            csrfToken = await csrfToken;
        }
        
        if (!csrfToken || typeof csrfToken !== 'string') {
            showAlert('CSRF token not available', 'danger');
            return;
        }
        
        const response = await fetch('/admin/api/configuration/import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(importData)
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Show results
            const resultsDiv = document.getElementById('importResults');
            const messagesDiv = document.getElementById('importMessages');
            
            resultsDiv.classList.remove('d-none');
            messagesDiv.innerHTML = '';
            
            if (data.messages && Array.isArray(data.messages)) {
                data.messages.forEach(message => {
                    const p = document.createElement('p');
                    p.className = 'mb-1';
                    p.textContent = message;
                    messagesDiv.appendChild(p);
                });
            }
            
            if (!validateOnly) {
                // Reload configurations if actually imported
                loadConfigurations();
            }
            showAlert(validateOnly ? 'Validation completed' : 'Import completed successfully', 'success');
        } else {
            showAlert(data.error || 'Import failed', 'danger');
        }
    } catch (error) {
        console.error('Error importing configurations:', error);
        showAlert('Error importing configurations', 'danger');
    }
}

/**
 * Show documentation
 */
async function showDocumentation() {
    try {
        const response = await fetch('/admin/api/configuration/documentation');
        const data = await response.json();
        
        if (response.ok) {
            const content = document.getElementById('documentationContent');
            content.innerHTML = '';
            
            Object.entries(data.documentation).forEach(([categoryKey, category]) => {
                const section = document.createElement('div');
                section.className = 'mb-4';
                
                section.innerHTML = `
                    <h4>${category.name}</h4>
                    <p class="text-muted">${category.description}</p>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Key</th>
                                    <th>Type</th>
                                    <th>Default</th>
                                    <th>Description</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${category.configurations.map(config => `
                                    <tr>
                                        <td>
                                            <code>${config.key}</code>
                                            ${config.is_sensitive ? '<i class="fas fa-lock text-warning ms-1" title="Sensitive"></i>' : ''}
                                            ${config.requires_restart ? '<i class="fas fa-sync text-info ms-1" title="Requires Restart"></i>' : ''}
                                        </td>
                                        <td><span class="badge bg-info">${config.data_type}</span></td>
                                        <td><code>${JSON.stringify(config.default_value)}</code></td>
                                        <td class="small">${config.description}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
                
                content.appendChild(section);
            });
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('documentationModal'));
            modal.show();
        } else {
            showAlert(data.error || 'Error loading documentation', 'danger');
        }
    } catch (error) {
        console.error('Error loading documentation:', error);
        showAlert('Error loading documentation', 'danger');
    }
}

/**
 * Show validation error
 */
function showValidationError(errors) {
    const errorDiv = document.getElementById('validationErrors');
    if (!errorDiv) {
        console.error('validationErrors element not found');
        // Fallback to alert if the element doesn't exist
        showAlert(errors.join(', '), 'danger');
        return;
    }
    errorDiv.innerHTML = errors.map(error => `<div>${escapeHtml(error)}</div>`).join('');
    errorDiv.classList.remove('d-none');
}

/**
 * Initialize default configurations
 */
async function initializeDefaultConfigurations() {
    if (!confirm('This will create database records for all default configurations that don\'t already exist. Continue?')) {
        return;
    }
    
    try {
        // Get CSRF token - handle both sync and async cases
        let csrfToken = getCSRFToken();
        
        // If it's a Promise, await it
        if (csrfToken && typeof csrfToken.then === 'function') {
            csrfToken = await csrfToken;
        }
        
        if (!csrfToken || typeof csrfToken !== 'string') {
            showAlert('CSRF token not available', 'danger');
            return;
        }
        
        const response = await fetch('/admin/api/configuration/initialize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Show success message with details
            let message = `Initialization completed: ${data.created_count} configurations created`;
            if (data.messages && data.messages.length > 0) {
                message += '\n\nDetails:\n' + data.messages.join('\n');
            }
            
            showAlert(message, 'success');
            
            // Reload configurations to show the new ones
            loadConfigurations();
        } else {
            showAlert(data.error || 'Failed to initialize default configurations', 'danger');
        }
    } catch (error) {
        console.error('Error initializing default configurations:', error);
        showAlert('Error initializing default configurations', 'danger');
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.top = '20px';
    alert.style.right = '20px';
    alert.style.zIndex = '9999';
    alert.innerHTML = `
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.parentNode.removeChild(alert);
        }
    }, 5000);
}

/**
 * Load restart required status
 */
async function loadRestartRequiredStatus() {
    try {
        const response = await fetch('/admin/api/configuration/restart-status');
        const data = await response.json();
        
        if (response.ok) {
            window.pendingRestartConfigs = data.pending_restart_configs || [];
            updateRestartNotification(data.restart_required, data.pending_restart_configs || []);
        }
    } catch (error) {
        console.error('Error loading restart status:', error);
    }
}

/**
 * Update restart notification display
 */
function updateRestartNotification(restartRequired, pendingConfigs) {
    const notificationRow = document.getElementById('restartNotificationRow');
    const countElement = document.getElementById('restartRequiredCount');
    
    if (restartRequired && pendingConfigs.length > 0) {
        notificationRow.style.display = 'block';
        countElement.textContent = pendingConfigs.length;
    } else {
        notificationRow.style.display = 'none';
    }
    
    // Update configurations table if it's already loaded
    if (currentConfigurations && Object.keys(currentConfigurations).length > 0) {
        displayConfigurations(currentConfigurations);
    }
}

/**
 * Show restart required configurations modal
 */
async function showRestartRequiredConfigs() {
    try {
        const response = await fetch('/admin/api/configuration/restart-status');
        const data = await response.json();
        
        if (response.ok && data.pending_restart_configs) {
            const tbody = document.getElementById('restartRequiredTableBody');
            tbody.innerHTML = '';
            
            // Get configuration details for each pending restart config
            for (const key of data.pending_restart_configs) {
                const schema = configurationSchema[key];
                const value = currentConfigurations[key];
                
                let displayValue = value;
                if (typeof value === 'object') {
                    displayValue = JSON.stringify(value);
                } else if (typeof value === 'boolean') {
                    displayValue = value ? 'true' : 'false';
                }
                
                // Truncate long values
                if (displayValue && displayValue.length > 100) {
                    displayValue = displayValue.substring(0, 100) + '...';
                }
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <code>${escapeHtml(key)}</code>
                        ${schema && schema.is_sensitive ? '<i class="bi bi-lock-fill text-warning ms-1" title="Sensitive"></i>' : ''}
                    </td>
                    <td><code>${escapeHtml(displayValue || 'null')}</code></td>
                    <td>
                        <span class="badge bg-secondary">${schema ? schema.category : 'unknown'}</span>
                    </td>
                    <td class="text-muted small">${schema ? escapeHtml(schema.description) : ''}</td>
                `;
                tbody.appendChild(row);
            }
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('restartRequiredModal'));
            modal.show();
        } else {
            showAlert('No configurations requiring restart found', 'info');
        }
    } catch (error) {
        console.error('Error loading restart required configurations:', error);
        showAlert('Error loading restart required configurations', 'danger');
    }
}

/**
 * Acknowledge restart required configurations
 */
function acknowledgeRestartRequired() {
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('restartRequiredModal'));
    modal.hide();
    
    // Show acknowledgment message
    showAlert('Restart requirement acknowledged. Please restart the system when convenient to apply these changes.', 'warning');
}

/**
 * Assess configuration impact
 */
async function assessConfigurationImpact(key, newValue) {
    try {
        // Get CSRF token
        let csrfToken = getCSRFToken();
        if (csrfToken && typeof csrfToken.then === 'function') {
            csrfToken = await csrfToken;
        }
        
        if (!csrfToken || typeof csrfToken !== 'string') {
            console.error('CSRF token not available for impact assessment');
            return;
        }
        
        const response = await fetch(`/admin/api/configuration/${key}/impact-assessment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                new_value: newValue
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            displayImpactAssessment(data);
        } else {
            // Hide impact assessment on error
            document.getElementById('impactAssessment').classList.add('d-none');
            document.getElementById('criticalChangeConfirmation').classList.add('d-none');
        }
    } catch (error) {
        console.error('Error assessing configuration impact:', error);
        // Hide impact assessment on error
        document.getElementById('impactAssessment').classList.add('d-none');
        document.getElementById('criticalChangeConfirmation').classList.add('d-none');
    }
}

/**
 * Display impact assessment results
 */
function displayImpactAssessment(impact) {
    const impactDiv = document.getElementById('impactAssessment');
    const criticalDiv = document.getElementById('criticalChangeConfirmation');
    
    // Show impact assessment
    impactDiv.classList.remove('d-none');
    
    // Set impact level with appropriate styling
    const impactLevelSpan = document.getElementById('impactLevel');
    impactLevelSpan.textContent = impact.impact_level.toUpperCase();
    impactLevelSpan.className = 'badge ms-1';
    
    switch (impact.impact_level.toLowerCase()) {
        case 'low':
            impactLevelSpan.classList.add('bg-success');
            break;
        case 'medium':
            impactLevelSpan.classList.add('bg-warning', 'text-dark');
            break;
        case 'high':
            impactLevelSpan.classList.add('bg-danger');
            break;
        case 'critical':
            impactLevelSpan.classList.add('bg-dark');
            break;
        default:
            impactLevelSpan.classList.add('bg-secondary');
    }
    
    // Set restart requirement
    const restartSpan = document.getElementById('impactRestartRequired');
    restartSpan.textContent = impact.requires_restart ? 'YES' : 'NO';
    restartSpan.className = 'badge ms-1';
    restartSpan.classList.add(impact.requires_restart ? 'bg-warning' : 'bg-success');
    if (impact.requires_restart) {
        restartSpan.classList.add('text-dark');
    }
    
    // Set affected components
    const componentsDiv = document.getElementById('affectedComponents');
    componentsDiv.innerHTML = '';
    impact.affected_components.forEach(component => {
        const badge = document.createElement('span');
        badge.className = 'badge bg-info me-1';
        badge.textContent = component;
        componentsDiv.appendChild(badge);
    });
    
    // Set risk factors
    const riskFactorsSection = document.getElementById('riskFactorsSection');
    const riskFactorsList = document.getElementById('riskFactors');
    if (impact.risk_factors && impact.risk_factors.length > 0) {
        riskFactorsSection.style.display = 'block';
        riskFactorsList.innerHTML = '';
        impact.risk_factors.forEach(risk => {
            const li = document.createElement('li');
            li.textContent = risk;
            riskFactorsList.appendChild(li);
        });
    } else {
        riskFactorsSection.style.display = 'none';
    }
    
    // Set mitigation steps
    const mitigationSection = document.getElementById('mitigationStepsSection');
    const mitigationList = document.getElementById('mitigationSteps');
    if (impact.mitigation_steps && impact.mitigation_steps.length > 0) {
        mitigationSection.style.display = 'block';
        mitigationList.innerHTML = '';
        impact.mitigation_steps.forEach(step => {
            const li = document.createElement('li');
            li.textContent = step;
            mitigationList.appendChild(li);
        });
    } else {
        mitigationSection.style.display = 'none';
    }
    
    // Set related configurations
    const relatedSection = document.getElementById('relatedConfigsSection');
    const relatedDiv = document.getElementById('relatedConfigs');
    if (impact.related_configurations && impact.related_configurations.length > 0) {
        relatedSection.style.display = 'block';
        relatedDiv.innerHTML = '';
        impact.related_configurations.forEach(config => {
            const badge = document.createElement('span');
            badge.className = 'badge bg-secondary me-1';
            badge.textContent = config;
            relatedDiv.appendChild(badge);
        });
    } else {
        relatedSection.style.display = 'none';
    }
    
    // Set estimated downtime
    const downtimeSection = document.getElementById('estimatedDowntimeSection');
    const downtimeSpan = document.getElementById('estimatedDowntime');
    if (impact.estimated_downtime) {
        downtimeSection.style.display = 'block';
        downtimeSpan.textContent = impact.estimated_downtime;
    } else {
        downtimeSection.style.display = 'none';
    }
    
    // Show critical change confirmation for high/critical impact
    if (impact.impact_level.toLowerCase() === 'high' || impact.impact_level.toLowerCase() === 'critical') {
        criticalDiv.classList.remove('d-none');
        // Uncheck the confirmation checkbox
        document.getElementById('confirmCriticalChange').checked = false;
    } else {
        criticalDiv.classList.add('d-none');
    }
}

/**
 * Validate configuration value
 */
async function validateConfigurationValue(key, value) {
    try {
        // Get CSRF token
        let csrfToken = getCSRFToken();
        if (csrfToken && typeof csrfToken.then === 'function') {
            csrfToken = await csrfToken;
        }
        
        if (!csrfToken || typeof csrfToken !== 'string') {
            console.error('CSRF token not available for validation');
            return;
        }
        
        const response = await fetch(`/admin/api/configuration/${key}/validate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                value: value
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            displayValidationFeedback(data);
        } else {
            // Clear validation feedback on error
            clearValidationFeedback();
        }
    } catch (error) {
        console.error('Error validating configuration value:', error);
        clearValidationFeedback();
    }
}

/**
 * Display validation feedback
 */
function displayValidationFeedback(validation) {
    const errorsDiv = document.getElementById('validationErrors');
    const warningsDiv = document.getElementById('validationWarnings');
    const valueInput = document.getElementById('configValue');
    
    // Clear previous feedback
    errorsDiv.classList.add('d-none');
    warningsDiv.classList.add('d-none');
    valueInput.classList.remove('is-invalid', 'is-valid');
    
    // Display errors
    if (validation.errors && validation.errors.length > 0) {
        errorsDiv.innerHTML = '';
        validation.errors.forEach(error => {
            const errorDiv = document.createElement('div');
            errorDiv.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>${escapeHtml(error)}`;
            errorsDiv.appendChild(errorDiv);
        });
        errorsDiv.classList.remove('d-none');
        valueInput.classList.add('is-invalid');
    } else if (validation.is_valid) {
        valueInput.classList.add('is-valid');
    }
    
    // Display warnings
    if (validation.warnings && validation.warnings.length > 0) {
        warningsDiv.innerHTML = '';
        validation.warnings.forEach(warning => {
            const warningDiv = document.createElement('div');
            warningDiv.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${escapeHtml(warning)}`;
            warningsDiv.appendChild(warningDiv);
        });
        warningsDiv.classList.remove('d-none');
    }
    
    // Display conflicts
    if (validation.conflicts && validation.conflicts.length > 0) {
        const conflictsDiv = document.createElement('div');
        conflictsDiv.className = 'alert alert-warning mt-2';
        conflictsDiv.innerHTML = '<strong><i class="bi bi-exclamation-triangle-fill me-2"></i>Configuration Conflicts:</strong>';
        
        const conflictsList = document.createElement('ul');
        conflictsList.className = 'mt-2 mb-0';
        
        validation.conflicts.forEach(conflict => {
            const li = document.createElement('li');
            li.innerHTML = `<strong>${escapeHtml(conflict.conflicting_key)}:</strong> ${escapeHtml(conflict.description)} <span class="badge bg-${getSeverityColor(conflict.severity)} ms-1">${conflict.severity}</span>`;
            conflictsList.appendChild(li);
        });
        
        conflictsDiv.appendChild(conflictsList);
        
        // Insert after warnings or errors
        const insertAfter = warningsDiv.classList.contains('d-none') ? errorsDiv : warningsDiv;
        insertAfter.parentNode.insertBefore(conflictsDiv, insertAfter.nextSibling);
    }
    
    // Add validation rules info
    if (validation.validation_rules && Object.keys(validation.validation_rules).length > 0) {
        addValidationRulesInfo(validation.validation_rules, validation.data_type);
    }
}

/**
 * Clear validation feedback
 */
function clearValidationFeedback() {
    const errorsDiv = document.getElementById('validationErrors');
    const warningsDiv = document.getElementById('validationWarnings');
    const valueInput = document.getElementById('configValue');
    
    errorsDiv.classList.add('d-none');
    warningsDiv.classList.add('d-none');
    valueInput.classList.remove('is-invalid', 'is-valid');
    
    // Remove any conflict alerts
    const conflictAlerts = document.querySelectorAll('.alert-warning');
    conflictAlerts.forEach(alert => {
        if (alert.innerHTML.includes('Configuration Conflicts:')) {
            alert.remove();
        }
    });
    
    // Remove validation rules info
    const rulesInfo = document.getElementById('validationRulesInfo');
    if (rulesInfo) {
        rulesInfo.remove();
    }
}

/**
 * Add validation rules information
 */
function addValidationRulesInfo(rules, dataType) {
    // Remove existing rules info
    const existingInfo = document.getElementById('validationRulesInfo');
    if (existingInfo) {
        existingInfo.remove();
    }
    
    const rulesDiv = document.createElement('div');
    rulesDiv.id = 'validationRulesInfo';
    rulesDiv.className = 'alert alert-info mt-2';
    rulesDiv.innerHTML = '<strong><i class="bi bi-info-circle me-2"></i>Validation Rules:</strong>';
    
    const rulesList = document.createElement('ul');
    rulesList.className = 'mt-2 mb-0 small';
    
    // Add data type info
    const typeItem = document.createElement('li');
    typeItem.innerHTML = `<strong>Data Type:</strong> ${dataType}`;
    rulesList.appendChild(typeItem);
    
    // Add specific rules
    Object.entries(rules).forEach(([rule, value]) => {
        const li = document.createElement('li');
        
        switch (rule) {
            case 'min':
                li.innerHTML = `<strong>Minimum Value:</strong> ${value}`;
                break;
            case 'max':
                li.innerHTML = `<strong>Maximum Value:</strong> ${value}`;
                break;
            case 'min_length':
                li.innerHTML = `<strong>Minimum Length:</strong> ${value} characters`;
                break;
            case 'max_length':
                li.innerHTML = `<strong>Maximum Length:</strong> ${value} characters`;
                break;
            case 'pattern':
                li.innerHTML = `<strong>Pattern:</strong> <code>${escapeHtml(value)}</code>`;
                break;
            case 'allowed_values':
                li.innerHTML = `<strong>Allowed Values:</strong> ${Array.isArray(value) ? value.join(', ') : value}`;
                break;
            default:
                li.innerHTML = `<strong>${rule}:</strong> ${value}`;
        }
        
        rulesList.appendChild(li);
    });
    
    rulesDiv.appendChild(rulesList);
    
    // Insert after the config value container
    const container = document.getElementById('configValueContainer');
    container.parentNode.insertBefore(rulesDiv, container.nextSibling);
}

/**
 * Get severity color for badges
 */
function getSeverityColor(severity) {
    switch (severity.toLowerCase()) {
        case 'low':
            return 'info';
        case 'medium':
            return 'warning';
        case 'high':
            return 'danger';
        case 'critical':
            return 'dark';
        default:
            return 'secondary';
    }
}

/**
 * Test configuration (dry-run)
 */
async function testConfiguration() {
    const key = document.getElementById('configKey').value;
    const valueInput = document.getElementById('configValue');
    const schema = configurationSchema[key];
    
    let value = valueInput.value;
    
    // Convert value based on data type
    if (schema) {
        try {
            switch (schema.data_type) {
                case 'boolean':
                    value = value === 'true';
                    break;
                case 'integer':
                    value = parseInt(value);
                    break;
                case 'float':
                    value = parseFloat(value);
                    break;
                case 'json':
                    value = JSON.parse(value);
                    break;
                // string remains as is
            }
        } catch (error) {
            showAlert('Invalid value format for data type: ' + schema.data_type, 'danger');
            return;
        }
    }
    
    try {
        // Get CSRF token
        let csrfToken = getCSRFToken();
        if (csrfToken && typeof csrfToken.then === 'function') {
            csrfToken = await csrfToken;
        }
        
        if (!csrfToken || typeof csrfToken !== 'string') {
            showAlert('CSRF token not available', 'danger');
            return;
        }
        
        // Show loading state
        const testButton = document.querySelector('button[onclick="testConfiguration()"]');
        const originalText = testButton.innerHTML;
        testButton.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Testing...';
        testButton.disabled = true;
        
        const response = await fetch(`/admin/api/configuration/${key}/dry-run`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                value: value
            })
        });
        
        // Restore button state
        testButton.innerHTML = originalText;
        testButton.disabled = false;
        
        if (response.ok) {
            const data = await response.json();
            displayDryRunResults(data);
        } else {
            const errorData = await response.json();
            showAlert(errorData.error || 'Failed to test configuration', 'danger');
        }
    } catch (error) {
        console.error('Error testing configuration:', error);
        showAlert('Error testing configuration', 'danger');
        
        // Restore button state
        const testButton = document.querySelector('button[onclick="testConfiguration()"]');
        testButton.innerHTML = '<i class="bi bi-play-circle me-1"></i>Test Configuration';
        testButton.disabled = false;
    }
}

/**
 * Display dry-run results
 */
function displayDryRunResults(results) {
    // Set modal title with configuration key
    document.getElementById('dryRunModalLabel').innerHTML = `
        <i class="bi bi-play-circle-fill text-info me-2"></i>
        Configuration Test Results: <code>${results.key}</code>
    `;
    
    // Display overall recommendation
    displayDryRunRecommendation(results.recommendation);
    
    // Display validation results
    displayDryRunValidation(results.validation);
    
    // Display impact analysis
    displayDryRunImpact(results.impact);
    
    // Display conflicts
    displayDryRunConflicts(results.conflicts);
    
    // Display rollback information
    displayDryRunRollback(results.rollback);
    
    // Display checklists
    displayDryRunChecklist(results.change_management);
    
    // Show/hide proceed button based on recommendation
    const proceedButton = document.getElementById('proceedWithChange');
    if (results.recommendation.proceed) {
        proceedButton.style.display = 'inline-block';
        proceedButton.setAttribute('data-config-key', results.key);
        proceedButton.setAttribute('data-config-value', JSON.stringify(results.new_value));
    } else {
        proceedButton.style.display = 'none';
    }
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('dryRunModal'));
    modal.show();
}

/**
 * Display dry-run recommendation
 */
function displayDryRunRecommendation(recommendation) {
    const recommendationDiv = document.getElementById('dryRunRecommendation');
    const iconElement = document.getElementById('recommendationIcon');
    const titleElement = document.getElementById('recommendationTitle');
    const reasonElement = document.getElementById('recommendationReason');
    const confidenceElement = document.getElementById('confidenceLevel');
    
    // Set alert class and icon based on recommendation
    recommendationDiv.className = 'alert mb-3';
    if (recommendation.proceed) {
        recommendationDiv.classList.add('alert-success');
        iconElement.className = 'bi bi-check-circle-fill text-success me-2';
        titleElement.textContent = 'Recommended: Proceed with Change';
    } else {
        recommendationDiv.classList.add('alert-danger');
        iconElement.className = 'bi bi-x-circle-fill text-danger me-2';
        titleElement.textContent = 'Not Recommended: Review Required';
    }
    
    reasonElement.textContent = recommendation.reason;
    
    // Set confidence level
    confidenceElement.textContent = `${recommendation.confidence.toUpperCase()} CONFIDENCE`;
    confidenceElement.className = 'badge';
    switch (recommendation.confidence.toLowerCase()) {
        case 'high':
            confidenceElement.classList.add('bg-success');
            break;
        case 'medium':
            confidenceElement.classList.add('bg-warning', 'text-dark');
            break;
        case 'low':
            confidenceElement.classList.add('bg-danger');
            break;
        default:
            confidenceElement.classList.add('bg-secondary');
    }
}

/**
 * Display dry-run validation results
 */
function displayDryRunValidation(validation) {
    const validationDiv = document.getElementById('dryRunValidation');
    
    let html = '<div class="row">';
    
    // Validation status
    html += '<div class="col-md-6">';
    html += '<h6><i class="bi bi-check-circle me-2"></i>Validation Status</h6>';
    if (validation.is_valid) {
        html += '<div class="alert alert-success"><i class="bi bi-check-circle-fill me-2"></i>Valid</div>';
    } else {
        html += '<div class="alert alert-danger"><i class="bi bi-x-circle-fill me-2"></i>Invalid</div>';
    }
    html += '</div>';
    
    // Errors and warnings
    html += '<div class="col-md-6">';
    html += '<h6><i class="bi bi-exclamation-triangle me-2"></i>Issues</h6>';
    
    if (validation.errors && validation.errors.length > 0) {
        html += '<div class="alert alert-danger"><strong>Errors:</strong><ul class="mb-0 mt-1">';
        validation.errors.forEach(error => {
            html += `<li>${escapeHtml(error)}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (validation.warnings && validation.warnings.length > 0) {
        html += '<div class="alert alert-warning"><strong>Warnings:</strong><ul class="mb-0 mt-1">';
        validation.warnings.forEach(warning => {
            html += `<li>${escapeHtml(warning)}</li>`;
        });
        html += '</ul></div>';
    }
    
    if ((!validation.errors || validation.errors.length === 0) && 
        (!validation.warnings || validation.warnings.length === 0)) {
        html += '<div class="alert alert-info">No issues detected</div>';
    }
    
    html += '</div></div>';
    
    validationDiv.innerHTML = html;
}

/**
 * Display dry-run impact analysis
 */
function displayDryRunImpact(impact) {
    const impactDiv = document.getElementById('dryRunImpact');
    
    let html = '<div class="row">';
    
    // Impact level and restart requirement
    html += '<div class="col-md-6">';
    html += '<h6><i class="bi bi-speedometer2 me-2"></i>Impact Level</h6>';
    html += `<span class="badge bg-${getImpactLevelColor(impact.level)} fs-6">${impact.level.toUpperCase()}</span>`;
    
    if (impact.requires_restart) {
        html += '<div class="mt-2"><span class="badge bg-warning text-dark"><i class="bi bi-arrow-clockwise me-1"></i>Restart Required</span></div>';
    }
    
    if (impact.estimated_downtime) {
        html += `<div class="mt-2"><strong>Estimated Downtime:</strong> ${impact.estimated_downtime}</div>`;
    }
    html += '</div>';
    
    // Affected components
    html += '<div class="col-md-6">';
    html += '<h6><i class="bi bi-diagram-3 me-2"></i>Affected Components</h6>';
    impact.affected_components.forEach(component => {
        html += `<span class="badge bg-info me-1">${component}</span>`;
    });
    html += '</div>';
    
    html += '</div>';
    
    // Risk factors
    if (impact.risk_factors && impact.risk_factors.length > 0) {
        html += '<div class="mt-3">';
        html += '<h6><i class="bi bi-shield-exclamation me-2"></i>Risk Factors</h6>';
        html += '<ul>';
        impact.risk_factors.forEach(risk => {
            html += `<li>${escapeHtml(risk)}</li>`;
        });
        html += '</ul></div>';
    }
    
    // Mitigation steps
    if (impact.mitigation_steps && impact.mitigation_steps.length > 0) {
        html += '<div class="mt-3">';
        html += '<h6><i class="bi bi-shield-check me-2"></i>Mitigation Steps</h6>';
        html += '<ul>';
        impact.mitigation_steps.forEach(step => {
            html += `<li>${escapeHtml(step)}</li>`;
        });
        html += '</ul></div>';
    }
    
    impactDiv.innerHTML = html;
}

/**
 * Display dry-run conflicts
 */
function displayDryRunConflicts(conflicts) {
    const conflictsDiv = document.getElementById('dryRunConflicts');
    
    if (!conflicts || conflicts.length === 0) {
        conflictsDiv.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle-fill me-2"></i>No configuration conflicts detected</div>';
        return;
    }
    
    let html = '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle-fill me-2"></i><strong>Configuration conflicts detected:</strong></div>';
    
    conflicts.forEach(conflict => {
        html += '<div class="card mb-2">';
        html += '<div class="card-body">';
        html += `<h6 class="card-title">${conflict.conflicting_key} <span class="badge bg-${getSeverityColor(conflict.severity)}">${conflict.severity}</span></h6>`;
        html += `<p class="card-text">${escapeHtml(conflict.description)}</p>`;
        html += `<small class="text-muted">Conflict Type: ${conflict.conflict_type}</small>`;
        html += '</div></div>';
    });
    
    conflictsDiv.innerHTML = html;
}

/**
 * Display dry-run rollback information
 */
function displayDryRunRollback(rollback) {
    const rollbackDiv = document.getElementById('dryRunRollback');
    
    let html = '<div class="row">';
    
    // Rollback complexity
    html += '<div class="col-md-6">';
    html += '<h6><i class="bi bi-speedometer2 me-2"></i>Rollback Complexity</h6>';
    html += `<span class="badge bg-${getRollbackComplexityColor(rollback.complexity)} fs-6">${rollback.complexity.toUpperCase()}</span>`;
    html += `<div class="mt-2"><strong>Estimated Time:</strong> ${rollback.estimated_time}</div>`;
    html += '</div>';
    
    // Rollback steps
    html += '<div class="col-md-6">';
    html += '<h6><i class="bi bi-list-ol me-2"></i>Rollback Steps</h6>';
    html += '<ol>';
    rollback.steps.forEach(step => {
        html += `<li>${escapeHtml(step)}</li>`;
    });
    html += '</ol></div>';
    
    html += '</div>';
    
    rollbackDiv.innerHTML = html;
}

/**
 * Display dry-run checklist
 */
function displayDryRunChecklist(changeManagement) {
    const checklistDiv = document.getElementById('dryRunChecklist');
    
    let html = '<div class="row">';
    
    // Pre-change checklist
    html += '<div class="col-md-6">';
    html += '<h6><i class="bi bi-list-check me-2"></i>Pre-Change Checklist</h6>';
    html += '<div class="list-group">';
    changeManagement.pre_change_checklist.forEach(item => {
        html += `<div class="list-group-item"><i class="bi bi-square me-2"></i>${escapeHtml(item)}</div>`;
    });
    html += '</div></div>';
    
    // Post-change verification
    html += '<div class="col-md-6">';
    html += '<h6><i class="bi bi-check2-square me-2"></i>Post-Change Verification</h6>';
    html += '<div class="list-group">';
    changeManagement.post_change_verification.forEach(item => {
        html += `<div class="list-group-item"><i class="bi bi-square me-2"></i>${escapeHtml(item)}</div>`;
    });
    html += '</div></div>';
    
    html += '</div>';
    
    // Recommended timing
    html += '<div class="mt-3">';
    html += '<div class="alert alert-info">';
    html += `<strong><i class="bi bi-clock me-2"></i>Recommended Timing:</strong> ${changeManagement.recommended_timing}`;
    html += '</div></div>';
    
    checklistDiv.innerHTML = html;
}

/**
 * Proceed with configuration change after dry-run
 */
function proceedWithConfigurationChange() {
    const proceedButton = document.getElementById('proceedWithChange');
    const configKey = proceedButton.getAttribute('data-config-key');
    const configValue = JSON.parse(proceedButton.getAttribute('data-config-value'));
    
    // Close dry-run modal
    const dryRunModal = bootstrap.Modal.getInstance(document.getElementById('dryRunModal'));
    dryRunModal.hide();
    
    // Set the value in the edit modal and save
    document.getElementById('configValue').value = typeof configValue === 'object' ? JSON.stringify(configValue, null, 2) : configValue;
    document.getElementById('configReason').value = 'Applied after successful dry-run test';
    
    // Save the configuration
    saveConfiguration();
}

/**
 * Get impact level color
 */
function getImpactLevelColor(level) {
    switch (level.toLowerCase()) {
        case 'low': return 'success';
        case 'medium': return 'warning';
        case 'high': return 'danger';
        case 'critical': return 'dark';
        default: return 'secondary';
    }
}

/**
 * Get rollback complexity color
 */
function getRollbackComplexityColor(complexity) {
    switch (complexity.toLowerCase()) {
        case 'low': return 'success';
        case 'medium': return 'warning';
        case 'high': return 'danger';
        default: return 'secondary';
    }
}

/**
 * Debounce function to limit API calls
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}