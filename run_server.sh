export DEV_MODE="false"
gunicorn -w 5 backend.app:app --daemon --log-level info --access-logfile /root/photo-lab-core/log/app.log --error-logfile /root/photo-lab-core/log/error.log --pid /root/photo-lab-core/gunicorn.pid --limit-request-line 20000
