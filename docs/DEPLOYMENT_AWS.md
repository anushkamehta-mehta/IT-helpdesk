# Deploying to AWS (single EC2 + RDS MySQL)

Target: Ubuntu 22.04/24.04 EC2, Nginx, RDS MySQL 8, HTTPS via Let's Encrypt.

## 1. Network and database
1. Create an **RDS MySQL 8** instance (db.t3.micro is fine for a demo), *not* publicly accessible.
2. Security groups: RDS allows inbound **3306 only from the EC2 security group**. EC2 allows 80/443 from anywhere and 22 only from your IP.
3. Store secrets (DB password, `JWT_SECRET`, `FLASK_SECRET_KEY`) in **AWS Secrets Manager or SSM Parameter Store** and give the EC2 instance an IAM role to read them.

## 2. Server setup
```bash
sudo apt update && sudo apt install -y python3-venv nginx mysql-client git certbot python3-certbot-nginx
sudo mkdir -p /opt/it-helpdesk && sudo chown ubuntu:ubuntu /opt/it-helpdesk
git clone <your-github-repo-url> /opt/it-helpdesk
cd /opt/it-helpdesk
python3 -m venv venv
venv/bin/pip install -r api/requirements.txt -r web/requirements.txt gunicorn
```

## 3. Database
From the EC2 instance (RDS admin user):
```bash
mysql -h <rds-endpoint> -u admin -p < database/schema.sql
mysql -h <rds-endpoint> -u admin -p -e "CREATE USER 'helpdesk_app'@'%' IDENTIFIED BY '<password>'; GRANT SELECT,INSERT,UPDATE,DELETE ON it_helpdesk.* TO 'helpdesk_app'@'%';"
```

## 4. Configuration
```bash
sudo mkdir -p /etc/it-helpdesk
sudo cp deploy/production.env.example /etc/it-helpdesk/helpdesk.env
sudo nano /etc/it-helpdesk/helpdesk.env       # fill in values
sudo chown ubuntu:ubuntu /etc/it-helpdesk/helpdesk.env && sudo chmod 600 /etc/it-helpdesk/helpdesk.env
```
Production must have `COOKIE_SECURE=true`, empty `CORS_ORIGINS` and empty `API_BASE_URL`.

## 5. First admin account
```bash
cd /opt/it-helpdesk/api
set -a; . /etc/it-helpdesk/helpdesk.env; set +a
../venv/bin/python -m scripts.create_admin
```
Then add IT team members and employees from `/admin` in the browser.

## 6. Services and Nginx
```bash
sudo cp deploy/helpdesk-api.service deploy/helpdesk-web.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now helpdesk-api helpdesk-web
sudo cp deploy/nginx.conf /etc/nginx/sites-available/helpdesk
sudo sed -i 's/helpdesk.example.com/YOUR.DOMAIN/' /etc/nginx/sites-available/helpdesk
sudo ln -s /etc/nginx/sites-available/helpdesk /etc/nginx/sites-enabled/ && sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR.DOMAIN
```

## 7. Verify
* `https://YOUR.DOMAIN/api/health` returns `{"api":"ok","database":"ok"}`
* `https://YOUR.DOMAIN/login` loads and you can log in.
* Logs: `journalctl -u helpdesk-api -f` and `journalctl -u helpdesk-web -f`.

## Updating
`git pull && sudo systemctl restart helpdesk-api helpdesk-web`

## Production hardening (after the demo)
Login rate limiting (e.g. Nginx `limit_req` or AWS WAF), RDS automated backups, CloudWatch logs, Alembic migrations, password reset by email.
