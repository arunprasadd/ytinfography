#!/bin/bash

# Initial SSL certificate setup script
# Run this script to obtain SSL certificates for the first time

DOMAIN="api.videotoinfographics.com"
EMAIL="darunprasad@hotmail.com"

echo "Starting initial SSL certificate setup for $DOMAIN..."

# Create temporary nginx config without SSL
cat > nginx/sites-available/api.videotoinfographics.com.temp << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://api;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Use temporary config
ln -sf ../sites-available/api.videotoinfographics.com.temp nginx/sites-enabled/api.videotoinfographics.com

# Start services without SSL
docker-compose up -d api nginx

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Obtain SSL certificate
echo "Obtaining SSL certificate..."
docker-compose run --rm certbot certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN

# Switch to SSL-enabled config
ln -sf ../sites-available/api.videotoinfographics.com nginx/sites-enabled/api.videotoinfographics.com

# Restart nginx with SSL config
docker-compose restart nginx

echo "SSL setup complete! Your API should now be available at https://$DOMAIN"