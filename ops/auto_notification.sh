cd /root/photo-lab-core
python3 -m backend.notification_center --user_since '2023-05-01 00:00:00' --notify_count 0 > /root/photo-lab-core/log/notification_center.log 2>&1 &