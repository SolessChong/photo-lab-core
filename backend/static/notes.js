let currentNotePage = 1;  // For pagination
const notesPerPage = 10;  // Number of notes loaded per click

function addNotePanel(note) {
    console.log('Adding note panel:', note);

    const notesRow = $('#notes-row');

    const column = $('<div>').addClass('col-12 col-sm-6 col-md-4 col-lg-3 col-xl-2 col-xxl-1');
    const panel = $('<div>').addClass('card note-panel');
    const img = $('<img>').addClass('card-img-top').attr('src', note.images[0].img_url);

    panel.append(img);

    const info = $('<div>').addClass('card-body');

    // Convert rate into an editable field
    const rateInput = $('<input>').addClass('form-control').attr('type', 'number').val(note.rate);
    rateInput.on('change', function() {
        updateNoteRate(note.id, this.value);
    });

    const rateInputGroup = $('<div>').addClass('input-group');
    rateInputGroup.html('<div class="input-group-prepend"><span class="input-group-text">Rate</span></div>');
    rateInputGroup.append(rateInput);

    info.html('<h5 class="card-title">' + note.name + '</h5><p class="card-text">' + note.text + '</p>');
    info.append(rateInputGroup);
    panel.append(info);

    column.append(panel);
    notesRow.append(column);
}

function loadNotes() {
    console.log('Loading notes...');

    $.ajax({
        url: '/api/get_all_notes',
        type: 'GET',
        data: { page: currentNotePage, per_page: notesPerPage, rate: -100 },
        success: function(data) {
            console.log('Notes loaded:', data);

            if (data.code === 0) {
                const notes = data.data;
                if (notes.length === 0) {
                    // No more notes to load
                    $('#load-more-notes').prop('disabled', true);
                    return;
                }

                notes.forEach(function(note) {
                    addNotePanel(note);
                });
                currentNotePage += 1;
            } else {
                console.error('Failed to fetch notes', data.msg);
            }
        },
        error: function(xhr, status, error) {
            console.error('Error fetching notes:', error);
        }
    });
}

$(document).on('click', '#load-more-notes', loadNotes);

// Load initial notes
$(document).ready(function() {
    console.log('Document ready.');
    loadNotes();
});

function updateNoteRate(noteId, newRate) {
    console.log('Updating note rate:', noteId, newRate);

    $.ajax({
        url: '/api/update_note_rate',
        type: 'POST',
        data: { note_id: noteId, new_rate: newRate },
        success: function(data) {
            console.log('Note rate updated:', data);

            if (data.success) {
                console.log('Note rate updated successfully');
            } else {
                console.error('Failed to update note rate', data.error);
            }
        },
        error: function(xhr, status, error) {
            console.error('Error updating note rate:', error);
        }
    });
}
