#!/bin/bash
cd /var/www/monitor_v2
/var/www/monitor_v2/venv/bin/python3 monitor_service.py manager >> /var/log/monitor_service.log 2>&1 &
