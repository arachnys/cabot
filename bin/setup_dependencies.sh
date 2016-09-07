#!/usr/bin/env bash

set -e
set -o pipefail

cd "$(dirname "$0")"

# Add the 'ubuntu' user if it does not already exist
if [ -z "$(cat /etc/passwd | grep '^ubuntu:')" ]; then
  useradd -m --shell /bin/bash ubuntu
fi

# Give the ubuntu user sudo privileges without a password
if [ ! -e /etc/sudoers.d/ubuntu ]; then
  echo 'ubuntu ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ubuntu
  chmod 440 /etc/sudoers.d/ubuntu
fi

# Generate a keypair the ubuntu user
if [ ! -f /home/ubuntu/.ssh/id_rsa ]; then
  su ubuntu -c 'mkdir -p ~/.ssh && ssh-keygen -t rsa -N "" -f ~/.ssh/id_rsa'
fi

if [ ! -z "$LOCAL_SSH_KEY" ]; then
  if grep -Fxq "$LOCAL_SSH_KEY" /home/ubuntu/.ssh/authorized_keys; then
    echo 'Local SSH public key already in remote authorized_keys'
  else
    echo 'Adding local SSH public key to authorized_keys'
    echo "$LOCAL_SSH_KEY" >> /home/ubuntu/.ssh/authorized_keys
    echo 'Key successfully added. You should now be able to SSH to this host as ubuntu@host'
  fi
fi

# SSH permissions
chown -R ubuntu:ubuntu /home/ubuntu/.ssh
chmod -R 600 /home/ubuntu/.ssh
chmod +x /home/ubuntu/.ssh

# Disable root access
passwd -l root
echo 'SSH access for root disabled. You will need to connect as ubuntu.'

packages=(
  'gcc'
  'g++'
  'make'
  'git'
  'python-pip'
  'python-dev'
  'python-virtualenv'
  'build-essential'
  'redis-server'
  'libpq-dev'
  'libxml2-dev'
  'libxslt-dev'
  'nodejs'
  'npm'
  'postgresql'
  'nginx'
  'htop'
  'libsasl2-dev'
  'libldap2-dev'
)

sudo apt-get update
sudo apt-get install --quiet --assume-yes ${packages[*]}

# install ruby if it's not installed
if ! which ruby; then
  sudo apt-get install -y ruby1.9.3
fi

# install rubygems if it's not included in ruby
if ! which gem; then
  sudo apt-get install -y rubygems
fi

# symlink node to nodejs for 14.04 compatibility
if ! which node && which nodejs; then
  sudo ln -s `which nodejs` /usr/bin/node
fi
set +e
sudo pip install -U pip # upgrade pip
set -e
sudo pip install -U pip --no-use-wheel # Don't ask

# install coffee and less
sudo npm install -g coffee-script less@1.3 --registry http://registry.npmjs.org/

sudo gem install foreman --version 0.77.0

# Set redis pass
set +e
grep -q '^requirepass' /etc/redis/redis.conf
DID_FAIL=$?
set -e
if [[ DID_FAIL -eq 1 ]] ; then # if line not found
  echo 'requirepass yourredispassword' | sudo tee -a /etc/redis/redis.conf
fi

# Install nginx
set -o pipefail

sudo openssl dhparam -dsaparam -out /etc/ssl/private/dhparam.key 4096

sudo apt-get install --quiet --assume-yes nginx

# Remove default ubuntu nginx configuration
sudo rm -f /etc/nginx/sites-enabled/default


# Configure nginx proxy
echo 'Writing nginx proxy configuration'
if [ -e /etc/nginx/sites-available/cabot ]; then
  echo 'WARNING: overwriting existing nginx configuration. Any local changes will be lost'
fi
sudo tee /etc/nginx/sites-available/cabot << EOF
server {
    listen 80;
    server_name cabot.iron.io;
    location /{
        server_name_in_redirect  off;
        root /var/www;
        #try_files \$uri @django;
        #return 301 https://\$server_name$request_uri;  # enforce https
    }
}
server {
    listen 443 ssl;
    ssl on;
    ssl_certificate /etc/letsencrypt/live/cabot.iron.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cabot.iron.io/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/cabot.iron.io/fullchain.pem;
    ssl_dhparam /etc/ssl/private/dhparam.key;
    ssl_session_timeout 24h;
    ssl_session_cache shared:SSL:10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers kEECDH+AES128:kEECDH:kEDH:-3DES:kRSA+AES128:kEDH+3DES:DES-CBC3-SHA:!RC4:!aNULL:!eNULL:!MD5:!EXPORT:!LOW:!SEED:!CAMELLIA:!IDEA:!PSK:!SRP:!SSLv2;
    ssl_prefer_server_ciphers on;
    server_name cabot.iron.io;
    location /{
        root /var/www;
        try_files \$uri @django;


#        add_header Strict-Transport-Security "max-age=31536000; includeSubdomains;";
    }

  location @django{
    proxy_pass http://localhost:5000;
    proxy_set_header Host \$http_host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_redirect http:// https://;
  }

  location /static/ {
    alias /home/ubuntu/cabot/static/;
  }
}
EOF

# Enable cabot configuration and restart nginx
if [ ! -e /etc/nginx/sites-enabled/cabot ]; then
  echo 'Enabling proxy in nginx configuration'
  sudo ln -s /etc/nginx/sites-available/cabot /etc/nginx/sites-enabled/cabot
fi

sudo service nginx restart
