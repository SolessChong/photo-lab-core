#!/bin/bash

# Define the prefix path
prefix_path="/home/chong/photolab/photo-lab-core"

# Change the current directory to prefix_path
cd $prefix_path

# Read the PID file line by line
while read pid; do
  # Use the PID to kill the process
  kill $pid
done < "ops/worker_render.pids"

# Remove the PID file
rm -f "ops/worker_render.pids"
