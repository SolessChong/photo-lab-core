# Render
1. sup-res for lora_render larger than 512
1. Hair
1. Semantic segmentation masking
1. Color correction, fix neck connection
1. Eye redraw
1. Pose controlnet regenerate for crop img

# Training Lora
1. Rotation augmentation

# User Data
1. head angle coverage check

# Engineering
1. Config manager
    1. Dynamic loading config from file
    1. Manage config overwrite using Mgr.
1. Use WEBUI's batch rendering feature to accelerate.
1. Cache more models for performance.

# Art
1. Lighht and shadow