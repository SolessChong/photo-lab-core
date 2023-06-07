#!/bin/bash

# Define the prefix path
prefix_path="/home/chong/photolab/photo-lab-core"

# Change the current directory to prefix_path
cd $prefix_path

# Define an array of ports
ports=(7890 7891 7892 7893)

# Create the directory for storing PID files if it doesn't exist
mkdir -p ops

for i in ${!ports[@]}; do
  port=${ports[$i]}

  export CUDA_VISIBLE_DEVICES=i
  # Run the python command in the background, redirect both stdout and stderr to a log file
  python -m core.worker_manager render --port $port > "log/worker_manager_${port}.log" 2>&1 &

  # Get the PID of the most recent background process that was started
  pid=$!

  # Write the PID to a file
  echo $pid > "ops/worker_render_${port}.pid"

  # Sleep for a few seconds to allow the previous service to start
  sleep 5
done
