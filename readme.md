<!-- nginx code-->

server {
    listen 443 ssl;
    server_name querysafe.metricvibes.com;

    ssl_certificate /etc/letsencrypt/live/querysafe.metricvibes.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/querysafe.metricvibes.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://unix:/home/dipanshu_saini/querysafe/querysafe.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/dipanshu_saini/querysafe/staticfiles/;
    }

    location /media/ {
        alias /home/dipanshu_saini/querysafe/media/;
    }   
}



server {
    listen 80;
    server_name querysafe.metricvibes.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name querysafe.metricvibes.com;

    ssl_certificate /etc/letsencrypt/live/querysafe.metricvibes.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/querysafe.metricvibes.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/querysafe/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /home/querysafe/media/;
        expires 30d;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/querysafe/querysafe.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}


<!-- restart services  -->
# Reload systemd
sudo systemctl daemon-reload

# Restart Gunicorn
sudo systemctl restart gunicorn

# Restart Nginx
sudo systemctl restart nginx











<!-- logs check-->
# Check Gunicorn logs
sudo journalctl -u gunicorn -n 50

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log   

# check all activity
systemctl list-units --type=service

# reload all deamon
sudo systemctl daemon-reload

# live logs check
journalctl -u gunicorn -f

# gunicor start
sudo systemctl start gunicorn

# gunicorn status
sudo systemctl start gunicorn












<!-- 4.31 Updated nginx -->

server {
    listen 80;
    server_name querysafe.metricvibes.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name querysafe.metricvibes.com;

    ssl_certificate /etc/letsencrypt/live/querysafe.metricvibes.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/querysafe.metricvibes.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /home/dipanshu_saini/querysafe/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /home/dipanshu_saini/querysafe/media/;
        expires 30d;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/dipanshu_saini/querysafe/querysafe.sock;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}


<!-- system restart cmd  -->
sudo systemctl restart gunicorn
sudo systemctl restart nginx
