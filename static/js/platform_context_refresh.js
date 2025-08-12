// Platform Context Refresh Utility
// Ensures platform context is properly updated after platform operations

(function() {
    'use strict';
    
    // Function to refresh platform context from server
    window.refreshPlatformContext = async function() {
        try {
            const response = await window.csrfHandler.secureFetch('/api/session_state', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.platform) {
                    // Update platform UI elements
                    updatePlatformUI(result.platform);
                    
                    // Notify session sync about the update
                    if (window.sessionSync) {
                        window.sessionSync.updatePlatformContext(result.platform);
                    }
                    
                    return result.platform;
                }
            }
        } catch (error) {
            console.error('Error refreshing platform context:', error);
        }
        return null;
    };
    
    // Function to update platform UI elements
    function updatePlatformUI(platform) {
        // Update platform dropdown text
        const platformDropdown = document.getElementById('platformsDropdown');
        if (platformDropdown) {
            platformDropdown.textContent = `Platforms: ${platform.name}`;
        }
        
        // Update current platform displays
        const currentPlatformElements = document.querySelectorAll('[data-current-platform]');
        currentPlatformElements.forEach(element => {
            element.textContent = platform.name;
            element.setAttribute('data-platform-id', platform.id);
            element.setAttribute('data-platform-type', platform.platform_type);
        });
        
        // Update user info displays
        const userInfoElements = document.querySelectorAll('[data-user-info]');
        userInfoElements.forEach(element => {
            const infoType = element.getAttribute('data-user-info');
            if (infoType === 'platform') {
                element.textContent = platform.name;
            }
        });
    }
    
    // Auto-refresh platform context when page loads if needed
    document.addEventListener('DOMContentLoaded', function() {
        // Check if we need to refresh platform context
        const needsRefresh = sessionStorage.getItem('platform_context_needs_refresh');
        if (needsRefresh === 'true') {
            sessionStorage.removeItem('platform_context_needs_refresh');
            setTimeout(() => {
                window.refreshPlatformContext();
            }, 500);
        }
    });
    
    // Mark that platform context needs refresh (called after platform operations)
    window.markPlatformContextForRefresh = function() {
        sessionStorage.setItem('platform_context_needs_refresh', 'true');
    };
    
})();