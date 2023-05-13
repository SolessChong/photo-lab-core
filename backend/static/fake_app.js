async function loadUserResults(userIds) {
    const container = document.querySelector('#user-result-container');
    container.innerHTML = '';

    for (const userId of userIds) {
        try {
            const response = await fetch(`http://photolab.aichatjarvis.com/api/get_generated_images?user_id=${userId}`);
            const data = await response.json();

            for (const pack of data.data.packs) {
                // Create pack card
                const packCard = document.createElement('div');
                packCard.className = 'card mb-3';
                container.appendChild(packCard);
            
                // Create pack card body
                const cardBody = document.createElement('div');
                cardBody.className = 'card-body';
                packCard.appendChild(cardBody);
            
                // Add user ID, pack ID and pack description
                const infoRow = document.createElement('div');
                infoRow.className = 'row';
                cardBody.appendChild(infoRow);
            
                const userIdElement = document.createElement('div');
                userIdElement.className = 'col-md-4 mb-2';
                userIdElement.innerHTML = `<h5 class="card-title mb-0">User ID: ${userId}</h5>`;
                infoRow.appendChild(userIdElement);
            
                const packId = document.createElement('div');
                packId.className = 'col-md-4 mb-2';
                packId.innerHTML = `<h5 class="card-title mb-0">Pack ID: ${pack.pack_id}</h5>`;
                infoRow.appendChild(packId);
            
                const packDescription = document.createElement('div');
                packDescription.className = 'col-md-4 mb-2';
                packDescription.innerHTML = `<h5 class="card-title mb-0">Description: ${pack.description}</h5>`;
                infoRow.appendChild(packDescription);
            
                // Add pack photos container
                const photosContainer = document.createElement('div');
                photosContainer.className = 'row';
                cardBody.appendChild(photosContainer);
            
                pack.imgs.forEach((imgUrl, index) => {
                    const photo = document.createElement('img');
                    const photoSrc = imgUrl;
            
                    // Create a column for each image
                    const photoCol = document.createElement('div');
                    photoCol.className = 'col-xl-2 col-lg-3 col-md-4 mb-2';
                    photosContainer.appendChild(photoCol);
            
                    // Add FancyBox functionality
                    const lightboxLink = document.createElement('a');
                    lightboxLink.href = photoSrc;
                    lightboxLink.setAttribute('data-fancybox', `gallery-${pack.pack_id}`);
                    photoCol.appendChild(lightboxLink);
            
                    // Configure the thumbnail image
                    photo.src = photoSrc;
                    photo.className = 'img-thumbnail w-100';
                    lightboxLink.appendChild(photo);
                });
            }
        } catch (error) {
            console.error('Error fetching user results:', error);
        }
    }
}




async function loadAllUserIds() {
    try {
        const response = await fetch('/get_all_user');
        const data = await response.json();
        const sortedUserIds = data.data.user_ids;
        const userSelect = document.querySelector('#user-select');

        // Clear the default option
        userSelect.innerHTML = '';

        sortedUserIds.forEach(userId => {
            const option = document.createElement('option');
            option.value = userId;
            option.textContent = userId;
            userSelect.appendChild(option);
        });

        // Load the first 20 user IDs by default
        loadUserResults(sortedUserIds.slice(0, 20));
    } catch (error) {
        console.error('Error fetching all user IDs:', error);
    }
}
