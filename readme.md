<!-- nginx  -->

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


<!-- restart services  -->
# Reload systemd
sudo systemctl daemon-reload

# Restart Gunicorn
sudo systemctl restart gunicorn

# Restart Nginx
sudo systemctl restart nginx


<!-- logs -->
# Check Gunicorn logs
sudo journalctl -u gunicorn -n 50

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log   