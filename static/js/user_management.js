// Copyright (C) 2025 iolaire mcfadden.
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
/**
 * User Management JavaScript
 * Handles interactions for the user management page
 */

document.addEventListener('DOMContentLoaded', function() {
    // Edit user modal
    const editUserModal = document.getElementById('editUserModal');
    if (editUserModal) {
        editUserModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const userId = button.getAttribute('data-user-id');
            const username = button.getAttribute('data-username');
            const email = button.getAttribute('data-email');
            const role = button.getAttribute('data-role');
            const isActive = button.getAttribute('data-is-active') === 'True';
            
            const userIdInput = editUserModal.querySelector('#user_id');
            const usernameInput = editUserModal.querySelector('#edit_username');
            const emailInput = editUserModal.querySelector('#edit_email');
            const roleSelect = editUserModal.querySelector('#edit_role');
            const isActiveCheckbox = editUserModal.querySelector('#edit_is_active');
            
            userIdInput.value = userId;
            usernameInput.value = username;
            emailInput.value = email;
            roleSelect.value = role;
            isActiveCheckbox.checked = isActive;
            
            // Clear password fields
            const passwordInput = editUserModal.querySelector('#edit_password');
            const confirmPasswordInput = editUserModal.querySelector('#edit_confirm_password');
            if (passwordInput) passwordInput.value = '';
            if (confirmPasswordInput) confirmPasswordInput.value = '';
        });
    }
    
    // Delete user modal
    const deleteUserModal = document.getElementById('deleteUserModal');
    if (deleteUserModal) {
        deleteUserModal.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const userId = button.getAttribute('data-user-id');
            const username = button.getAttribute('data-username');
            
            const userIdInput = deleteUserModal.querySelector('#user_id');
            const usernameSpan = deleteUserModal.querySelector('#delete_username');
            
            userIdInput.value = userId;
            usernameSpan.textContent = username;
        });
    }
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});