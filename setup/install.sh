#!/bin/bash

# Exit on error
set -e

echo "Setting up Translation Service..."

# Create necessary directories
sudo mkdir -p /var/www/translation-service/static
sudo mkdir -p /var/log/nginx
sudo mkdir -p /etc/nginx/sites-available
sudo mkdir -p /etc/nginx/sites-enabled

# Copy Nginx configuration
sudo cp nginx/translation-service.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/translation-service.conf /etc/nginx/sites-enabled/

# Copy static files
sudo cp -r static/* /var/www/translation-service/static/

# Set correct permissions
sudo chown -R www-data:www-data /var/www/translation-service
sudo chmod -R 755 /var/www/translation-service

# Create systemd service
cat << EOF | sudo tee /etc/systemd/system/translation-service.service
[Unit]
Description=Translation Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/translation-service
Environment="PATH=/var/www/translation-service/venv/bin"
ExecStart=/var/www/translation-service/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable translation-service
sudo systemctl start translation-service
sudo systemctl restart nginx

echo "Installation completed successfully!"
echo "Please configure your domain and SSL certificates before enabling HTTPS."
