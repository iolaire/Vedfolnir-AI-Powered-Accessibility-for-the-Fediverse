# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Null Session Interface

A minimal session interface that prevents all session operations
to avoid WebSocket WSGI violations.
"""

from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict
import logging

logger = logging.getLogger(__name__)

class NullSession(CallbackDict, SessionMixin):
    """A session that does nothing"""
    
    def __init__(self):
        def on_update(self):
            pass  # Do nothing on updates
        
        CallbackDict.__init__(self, {}, on_update)
        self.permanent = False
        self.new = False
        self.modified = False

class NullSessionInterface(SessionInterface):
    """
    A session interface that does absolutely nothing
    
    This prevents any session operations that could cause
    WSGI violations during WebSocket upgrades.
    """
    
    def open_session(self, app, request):
        """Always return a null session"""
        logger.debug(f"Null session opened for {request.path}")
        return NullSession()
    
    def save_session(self, app, session, response):
        """Never save sessions"""
        logger.debug(f"Null session save skipped")
        return  # Do nothing

def create_null_session_interface():
    """Create a null session interface"""
    return NullSessionInterface()