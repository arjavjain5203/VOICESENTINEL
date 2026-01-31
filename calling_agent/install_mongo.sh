#!/bin/bash
set -e

echo "🔧 Installing MongoDB Community Edition..."

# 1. Install prerequisites
sudo apt-get update
sudo apt-get install -y gnupg curl

# 2. Import the public key
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | \
   sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor --yes

# 3. Create list file (using Jammy as fallback for compatibility if Noble repo specific issues exist)
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list

# 4. Update and Install
sudo apt-get update
sudo apt-get install -y mongodb-org

# 5. Start Service
echo "🚀 Starting MongoDB..."
sudo systemctl start mongod
sudo systemctl enable mongod

# 6. Check status
if systemctl is-active --quiet mongod; then
    echo "✅ MongoDB is running!"
else
    echo "❌ MongoDB failed to start."
    exit 1
fi
