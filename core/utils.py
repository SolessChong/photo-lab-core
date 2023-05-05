import time
import sys
import random

def rabbit_head_animation(duration):
    start_time = time.time()
    bar_length = 80
    dog_head = "🐶"
    cat_head = "🐱"
    bar_char = "▬"

    # Initialize the positions of the dog and cat heads
    dog_pos = 0
    cat_pos = random.choice([0, 5])

    while time.time() - start_time < duration:
        # Create the rolling bar with the dog and cat heads at their respective positions
        bar = "".join([
            dog_head if i == dog_pos 
            else cat_head if i == cat_pos
            else ' ' if i > dog_pos and i < cat_pos 
            else bar_char 
            for i in range(bar_length)
        ])

        # Print the bar and overwrite it with \r
        sys.stdout.write("\r" + bar)
        sys.stdout.flush()

        # Update the positions of the dog and cat heads
        dog_pos += random.choice([0, 1])
        cat_pos += random.choice([0, 1])

        # Make sure the positions stay within the bar length
        dog_pos = max(min(cat_pos - 1, dog_pos), 0)
        cat_pos = max(min(cat_pos, bar_length - 1), 0)

        # Sleep for a short time to control the animation speed
        time.sleep(0.1)

    sys.stdout.write("\r")
    sys.stdout.flush()
