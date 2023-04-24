from celery import Celery, group

# Configure the Celery app
app = Celery('myapp', broker='redis://39.108.222.9:6379/0', backend='redis://39.108.222.9:6379/0')

# Create the task as a string
task_render_scene_str = 'render-scene'

def create_task_group(task_id_list):
    # Create a list of task_render_scene tasks
    render_scene_tasks = [app.signature(task_render_scene_str, args=(task_id,)) for task_id in task_id_list]

    # Create a group of tasks
    task_group = group(render_scene_tasks)

    # Apply the group
    task_group.apply_async()

if __name__ == '__main__':
    # Replace the following example task_id_list with your actual data
    task_id_list = [8, 9, 10]

    # Create and run the task group
    create_task_group(task_id_list)
