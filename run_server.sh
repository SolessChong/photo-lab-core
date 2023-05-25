export DEV_MODE="false"
gunicorn -w 20 backend.app:app --daemon --log-level info --log-file /root/photo-lab-core/log/app.log --error-logfile /root/photo-lab-core/log/error.log --pid /root/photo-lab-core/gunicorn.pid --limit-request-line 20000
