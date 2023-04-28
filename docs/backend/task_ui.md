# Features
## Task View
Show all tasks. Task info is shown in data panel. All task shown in two column flow view.

## Create task view
1. List distinct "collection_name" in Scene table.
1. Dropdown, list all persons, with `id` and `name` fields in User table.
1. Generate button, generate task with selected collection, specified by `collection_name` and person, by `id`.
1. In the backend request for generate, params: (collection_name, person_id): 
    1. Filter all scenes with `collection_name`
    1. Create a new task with `person_id` and `collection_name`, save all these task id's in a list.
    1. Send out celery task for all these tasks
        1. create list of set_up_scene tasks: 
            `group([signature('set_up_scene', (scene.scene_id,)) for scene in scene_list])`
        2. create list of render_scene tasks:
            `group([signature('render_scene', (task_id,), immutable=True) for task_id in task_id_list])`
        3. Assemble a celery.chain:
            ```
            ch = chain(
                group([signature('set_up_scene', (scene.scene_id,)) for scene in scene_list]),
                group([signature('render_scene', (task_id,), immutable=True) for task_id in task_id_list])
            )
            ```