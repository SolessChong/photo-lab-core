byobu new-window -t Train 'cd /home/chong/photolab/photo-lab-core/ && . venv/bin/activate && python -m worker_manager train'
byobu new-window -t Monitor 'watch nvidia-smi'
