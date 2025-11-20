#!/bin/bash
# Quick deployment setup script for DigitalOcean/Linux servers

echo "🚀 Setting up Hourly Picks Scheduler for 24/7 deployment..."

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
echo "📦 Installing Python and dependencies..."
apt install -y python3 python3-pip python3-venv git postgresql postgresql-contrib

# Create application directory
echo "📁 Creating application directory..."
mkdir -p /opt/hourly-picks
cd /opt/hourly-picks

# Clone repository (or copy files)
echo "📥 Setting up application files..."
# If using git:
# git clone YOUR_REPO_URL .

# If copying files manually, copy all files to /opt/hourly-picks/

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install requirements
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
echo "⚙️  Setting up environment variables..."
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit /opt/hourly-picks/.env with your API keys!"
    echo "Run: nano /opt/hourly-picks/.env"
fi

# Create systemd service
echo "🔧 Setting up systemd service..."
cat > /etc/systemd/system/hourly-picks.service <<EOF
[Unit]
Description=Hourly Picks Scheduler Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hourly-picks
Environment="PATH=/opt/hourly-picks/venv/bin:/usr/bin"
EnvironmentFile=/opt/hourly-picks/.env
ExecStart=/opt/hourly-picks/venv/bin/python /opt/hourly-picks/enhanced_scheduler.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=hourly-picks

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable service
systemctl enable hourly-picks

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit environment variables:"
echo "   nano /opt/hourly-picks/.env"
echo ""
echo "2. Start the service:"
echo "   systemctl start hourly-picks"
echo ""
echo "3. Check status:"
echo "   systemctl status hourly-picks"
echo ""
echo "4. View logs:"
echo "   journalctl -u hourly-picks -f"
echo ""
echo "🎉 Your scheduler will now run 24/7!"

