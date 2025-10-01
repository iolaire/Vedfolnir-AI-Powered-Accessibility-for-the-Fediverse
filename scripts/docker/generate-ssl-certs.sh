#!/bin/bash
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Generate SSL certificates for Nginx in Docker environment

set -e

# Configuration
CERT_DIR="ssl/certs"
KEY_DIR="ssl/keys"
CERT_NAME="vedfolnir"
DAYS=365
COUNTRY="US"
STATE="Virgnia"
CITY="Arlington"
ORG="Vedfolnir"
OU="IT Department"
CN="localhost"

# Create directories
mkdir -p "$CERT_DIR" "$KEY_DIR"

echo "Generating SSL certificate for Vedfolnir..."

# Generate private key
openssl genrsa -out "$KEY_DIR/$CERT_NAME.key" 2048

# Generate certificate signing request
openssl req -new -key "$KEY_DIR/$CERT_NAME.key" -out "$KEY_DIR/$CERT_NAME.csr" -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=$CN"

# Generate self-signed certificate with SAN
cat > "$KEY_DIR/$CERT_NAME.ext" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = vedfolnir.local
DNS.3 = *.vedfolnir.local
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

openssl x509 -req -in "$KEY_DIR/$CERT_NAME.csr" -signkey "$KEY_DIR/$CERT_NAME.key" -out "$CERT_DIR/$CERT_NAME.crt" -days $DAYS -extfile "$KEY_DIR/$CERT_NAME.ext"

# Set proper permissions
chmod 600 "$KEY_DIR/$CERT_NAME.key"
chmod 644 "$CERT_DIR/$CERT_NAME.crt"

# Clean up temporary files
rm "$KEY_DIR/$CERT_NAME.csr" "$KEY_DIR/$CERT_NAME.ext"

echo "SSL certificate generated successfully:"
echo "  Certificate: $CERT_DIR/$CERT_NAME.crt"
echo "  Private Key: $KEY_DIR/$CERT_NAME.key"
echo ""
echo "Certificate details:"
openssl x509 -in "$CERT_DIR/$CERT_NAME.crt" -text -noout | grep -E "(Subject:|DNS:|IP Address:|Not Before|Not After)"

echo ""
echo "To trust this certificate in your browser:"
echo "1. Open the certificate file: $CERT_DIR/$CERT_NAME.crt"
echo "2. Add it to your system's trusted certificate store"
echo "3. Or accept the security warning when accessing https://localhost"