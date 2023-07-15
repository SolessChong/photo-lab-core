
export DEV_MODE="false"
gunicorn -w 1 backend.app:app --daemon --log-level info --access-logfile /root/photo-lab-core/log/wechat_app.log --error-logfile /root/photo-lab-core/log/wechat_app_error.log --pid /root/photo-lab-core/wechat_gunicorn.pid --limit-request-line 20000 --bind 0.0.0.0:8003 --certfile=photolab.aichatjarvis.com.pem --keyfile=photolab.aichatjarvis.com.key
