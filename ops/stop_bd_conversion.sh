#!/bin/bash
set -e

PID_PATH="/root/photo-lab-core/ops/bd_conversion_gunicorn.pid"

if [ -f $PID_PATH ]; then
  echo "Stopping bytedance_conversion..."
  kill -TERM `cat $PID_PATH`
  rm $PID_PATH
  echo "Stopped."
else
  echo "No bytedance_conversion gunicorn process found to stop."
fi
