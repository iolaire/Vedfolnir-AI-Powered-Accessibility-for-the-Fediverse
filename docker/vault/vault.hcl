# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# HashiCorp Vault Configuration for Vedfolnir Docker Compose
# This configuration sets up Vault for secure secrets management

# Storage backend - using file storage for development/single-node deployment
storage "file" {
  path = "/vault/data"
}

# Listener configuration
listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1  # TLS disabled for internal Docker network
}

# API address for client connections
api_addr = "http://0.0.0.0:8200"

# Cluster address (for HA setups)
cluster_addr = "http://0.0.0.0:8201"

# UI configuration
ui = true

# Logging
log_level = "INFO"
log_format = "json"

# Disable mlock for containerized environments
disable_mlock = true

# Plugin directory
plugin_directory = "/vault/plugins"

# Default lease TTL and max lease TTL
default_lease_ttl = "168h"  # 7 days
max_lease_ttl = "720h"      # 30 days

# Enable audit logging
# audit "file" {
#   file_path = "/vault/logs/audit.log"
# }