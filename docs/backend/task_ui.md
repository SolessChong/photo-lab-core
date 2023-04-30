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

## Scene edit view
1. Show scene info in a complete row. Card layout.
1. In each row, list the scene base_img at the left most position.
1. In each row, next to base_img, is hint_img, if exists.
1. In each row, list all the tasks for this scene, in a horizontal flow layout. `Task.scene_id == scene.scene_id` is the filter.
1. Also show the additional info of scene:
    1. `scene.scene_id`
    1. `scene.collection_name`
    1. `scene.prompt`
    1. `scene.params`, a json string, show in a json editor, with expandable tree view, editable each field. Save button to update this field. If frontend editor is empty, save python none (Mysql NULL) object for this.
    1. `scene.rate`, a int. Add 'add', 'minus' button for this field, click will add or minus 1, update the db.


## Utils
Image url: https://photolab-test.oss-cn-shenzhen.aliyuncs.com/ + image's some `key` field in db.