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

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    loadConfigurationCategories();
    loadConfigurationSchema();
    loadConfigurations();
    
    // Set up event listeners
    document.getElementById('includeSensitive').addEventListener('change', loadConfigurations);
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
        
        row.innerHTML = `
            <td>
                <code>${escapeHtml(key)}</code>
                ${schema && schema.is_sensitive ? '<i class="fas fa-lock text-warning ms-1" title="Sensitive"></i>' : ''}
            </td>
            <td>${escapeHtml(displayValue || 'null')}</td>
            <td>
                <span class="badge bg-secondary">${schema ? schema.category : 'unknown'}</span>
            </td>
            <td>
                <span class="badge bg-info">${schema ? schema.data_type : 'string'}</span>
            </td>
            <td class="text-muted small">${schema ? escapeHtml(schema.description) : ''}</td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button type="button" class="btn btn-outline-primary" onclick="editConfiguration('${key}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button type="button" class="btn btn-outline-info" onclick="showConfigurationHistory('${key}')" title="History">
                        <i class="fas fa-history"></i>
                    </button>
                </div>
            </td>
        `;
        
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
        const response = await fetch(`/admin/api/configuration/${key}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
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
            
            // Reload configurations
            loadConfigurations();
            
            showAlert(`Configuration ${key} updated successfully`, 'success');
        } else {
            showValidationError([data.error || 'Failed to update configuration']);
        }
    } catch (error) {
        console.error('Error saving configuration:', error);
        showValidationError(['Error saving configuration']);
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
        const response = await fetch(`/admin/api/configuration/${key}/rollback`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
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
        
        const response = await fetch('/admin/api/configuration/import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(importData)
        });
        
        const data = await response.json();
        
        // Show results
        const resultsDiv = document.getElementById('importResults');
        const messagesDiv = document.getElementById('importMessages');
        
        resultsDiv.classList.remove('d-none');
        messagesDiv.innerHTML = '';
        
        data.messages.forEach(message => {
            const p = document.createElement('p');
            p.className = 'mb-1';
            p.textContent = message;
            messagesDiv.appendChild(p);
        });
        
        if (response.ok && data.success) {
            if (!validateOnly) {
                // Reload configurations if actually imported
                loadConfigurations();
            }
            showAlert(validateOnly ? 'Validation completed' : 'Import completed successfully', 'success');
        } else {
            showAlert('Import failed', 'danger');
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
    errorDiv.innerHTML = errors.map(error => `<div>${escapeHtml(error)}</div>`).join('');
    errorDiv.classList.remove('d-none');
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
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}