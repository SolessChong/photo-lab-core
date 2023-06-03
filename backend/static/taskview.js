let currentPage = 1;
let totalPages = 1;

function addTaskPanel(task) {
    const taskContainer = document.getElementById('task-container');

    const column = document.createElement('div');
    column.className = 'col-12 col-md-6 col-lg-4 col-xl-3 col-xxl-2';


    const panel = document.createElement('div');
    panel.className = 'card task-panel';

    const img = document.createElement('img');
    const originalImgSrc = 'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/' + task.result_img_key;
    const croppedImgSrc = originalImgSrc + '?x-oss-process=image/resize,w_400';
    img.src = croppedImgSrc;
    img.classList.add('card-img-top');

    // Add the Fancybox functionality
    const lightboxLink = document.createElement('a');
    lightboxLink.href = originalImgSrc;
    lightboxLink.setAttribute('data-fancybox', 'gallery');
    lightboxLink.appendChild(img);
    panel.appendChild(lightboxLink);

    const info = document.createElement('div');
    info.className = 'card-body';
    info.innerHTML = '<h5 class="card-title">Task ID: ' + task.id +
        '</h5><p class="card-text">Person IDs: ' + task.person_id_list.join(', ') +
        '</p>' + '<p class="card-text">Scene ID: ' + task.scene_id + '</p>' +
        '<p class="card-text">Pack ID: ' + task.pack_id + '</p>' +
        '<p class="card-text">User ID: ' + task.user_id + '</p>';

    panel.appendChild(info);

    column.appendChild(panel);
    taskContainer.appendChild(column);
}


function fetchTasks(page) {
    fetch(`/get_tasks?page=${page}`)
    .then((response) => response.json())
    .then((data) => {
        const tasks = data.tasks;
        totalPages = data.total_pages;

        const taskContainer = document.getElementById('task-container');
        taskContainer.innerHTML = '';

        tasks.forEach(addTaskPanel);

        if (currentPage === totalPages) {
            const loadMoreBtn = document.getElementById('load-more-btn');
            loadMoreBtn.disabled = true;
            loadMoreBtn.textContent = 'No More Tasks';
        }
    })
    .catch((error) => {
        console.error('Error fetching tasks:', error);
    });
}
function loadTasks(page) {
    const collection_name_filter = document.getElementById('collection-name-filter').value;
    const person_id_filter = document.getElementById('person-id-filter').value;

    let url = `/get_tasks?page=${page}`;
    if (collection_name_filter) url += `&collection_name=${encodeURIComponent(collection_name_filter)}`;
    if (person_id_filter) url += `&person_id=${encodeURIComponent(person_id_filter)}`;

    fetch(url)
        .then((response) => response.json())
        .then((data) => {
            const taskContainer = document.getElementById('task-container');
            taskContainer.innerHTML = '';

            const tasks = data.tasks;
            totalPages = data.total_pages;

            if (tasks.length === 0) {
                // Display an empty message when there are no tasks
                const emptyMessageContainer = document.createElement('div');
                emptyMessageContainer.className = 'col-12 text-center my-5';

                const emptyMessage = document.createElement('h3');
                emptyMessage.className = 'text-muted';
                emptyMessage.textContent = 'Empty';

                emptyMessageContainer.appendChild(emptyMessage);
                taskContainer.appendChild(emptyMessageContainer);
            } else {
                tasks.forEach((task) => {
                    addTaskPanel(task);
                });

                // Attach click event listener to the download button
                const downloadButton = document.getElementById('download-all-images');
                downloadButton.addEventListener('click', () => {
                    downloadAllImages(tasks);
                });
            }

            if (currentPage === totalPages) {
                const loadMoreBtn = document.getElementById('load-more-btn');
                loadMoreBtn.disabled = true;
                loadMoreBtn.textContent = 'No More Tasks';
            }
        })
        .catch((error) => {
            console.error('Error fetching tasks:', error);
        });
}

function downloadAllImages(tasks) {
    const zip = new JSZip();
    const downloadPromises = [];

    tasks.forEach((task) => {
        const imgSrc = 'https://photolab-test.oss-cn-shenzhen.aliyuncs.com/' + task.result_img_key;
        const downloadPromise = fetch(imgSrc)
            .then((response) => response.blob())
            .then((blob) => {
                const fileName = 'task_' + task.id + '.jpg';
                zip.file(fileName, blob);
            })
            .catch((error) => {
                console.error('Error downloading image:', error);
            });

        downloadPromises.push(downloadPromise);
    });

    Promise.all(downloadPromises)
        .then(() => {
            zip.generateAsync({ type: 'blob' })
                .then((content) => {
                    // Create a download link for the zip file
                    const downloadLink = document.createElement('a');
                    downloadLink.href = URL.createObjectURL(content);
                    downloadLink.download = 'images.zip';
                    downloadLink.click();
                })
                .catch((error) => {
                    console.error('Error generating zip file:', error);
                });
        })
        .catch((error) => {
            console.error('Error downloading images:', error);
        });
}



function fetchCollections() {
    fetch('/get_collections')
    .then(response => response.json())
    .then(collections => {
        const collectionFilter = document.getElementById('collection-name-filter');
        collections.forEach(collection => {
            const option = document.createElement('option');
            option.value = collection;
            option.textContent = collection;
            collectionFilter.appendChild(option);
        });
    })
    .catch(error => console.error('Error fetching collections:', error));
}

function fetchPersons() {
    fetch('/get_persons')
    .then(response => response.json())
    .then(persons => {
        const personFilter = document.getElementById('person-id-filter');
        persons.forEach(person => {
            const option = document.createElement('option');
            option.value = person.id;
            option.textContent = `[${person.id}] - ${person.name}`;
            personFilter.appendChild(option);
        });
    })
    .catch(error => console.error('Error fetching persons:', error));
}

fetchCollections();
fetchPersons();

// Add this function to handle the apply filters button click event
function applyFilters() {
    const collectionFilter = document.getElementById('collection-name-filter');
    const personFilter = document.getElementById('person-id-filter');

    // Reset the currentPage and call loadTasks with new filters
    currentPage = 1;
    loadTasks(currentPage);
}

// Initialize Task Viewer
// fetchTasks(currentPage);

////////////////////////////////////////////////
// TaskView Tab

document.addEventListener('DOMContentLoaded', () => {
    loadTasks(currentPage);
    const loadMoreBtn = document.getElementById('load-more-btn');
    loadMoreBtn.addEventListener('click', () => {
        currentPage += 1;
        loadTasks(currentPage);
    });
    // Attach the click event to the "Apply Filters" button
    document.getElementById('apply-filters-btn').addEventListener('click', applyFilters);
});

// Populate collection and person dropdowns
function loadCollectionsAndPersons() {
    fetch('/get_collections')
        .then(response => response.json())
        .then(collections => {
            const select = document.getElementById('collection-select');
            collections.forEach(collection => {
                const option = document.createElement('option');
                option.value = collection;
                option.textContent = collection;
                select.appendChild(option);
            });
        });

    fetch('/get_persons')
        .then(response => response.json())
        .then(persons => {
            const select = document.getElementById('person-select');
            persons.forEach(person => {
                const option = document.createElement('option');
                option.value = person.id;
                option.textContent = `[${person.id}] - ${person.name}`;
                select.appendChild(option);
            });
        });
}
