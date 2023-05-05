gunicorn -w 20 backend.app:app --daemon --log-level info --log-file /root/photo-lab-core/log/app.log --pid /root/photo-lab-core/gunicorn.pid
