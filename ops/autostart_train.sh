cd /home/chong/photolab/photo-lab-core/
source venv/bin/activate
/home/chong/photolab/photo-lab-core/venv/bin/python -m core.worker_manager train > /home/chong/photolab/photo-lab-core/log/worker_manager_train.log 2>&1 &