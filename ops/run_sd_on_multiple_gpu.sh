#!/bin/bash

# Define the prefix path
prefix_path="/home/chong/photolab/stable-diffusion-webui"

# Define an array of ports
ports=(7890 7891 7892 7893)

# Define an array of device ids
device_ids=(0 1 2 3)

for i in ${!ports[@]}; do
  port=${ports[$i]}
  device_id=${device_ids[$i]}

  # Set the environment variable
  export COMMANDLINE_ARGS="--port $port --device-id $device_id --api --theme dark --xformers --lora-dir /home/chong/photolab/photo-lab-core/core/train/models/lora"

  # Run the startup script in the background, redirect both stdout and stderr to a log file
  $prefix_path/webui.sh > "$prefix_path/service_${port}.log" 2>&1 &

  # Sleep for a few seconds to allow the previous service to start
  sleep 5
done

# Wait for all background jobs to finish
wait
