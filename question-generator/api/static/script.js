let currentFileId = null;

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
    fetchFilesList();
    setupUploadHandlers();
});

// --- SIDEBAR UPLOAD LOGIC ---
function setupUploadHandlers() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const sidebarActions = document.getElementById('sidebar-upload-actions');
    const sidebarFileName = document.getElementById('sidebar-file-name');

    dropZone.onclick = () => fileInput.click();

    fileInput.onchange = (e) => {
        const file = e.target.files[0];
        if (file) {
            sidebarFileName.textContent = file.name;
            sidebarActions.style.display = 'block';
        }
    };

    uploadBtn.onclick = async () => {
        const file = fileInput.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        uploadBtn.disabled = true;
        uploadBtn.textContent = "Uploading...";

        try {
            const response = await fetch('/upload-content', { method: 'POST', body: formData });
            const result = await response.json();
            if (response.ok) {
                alert("File added to library!");
                sidebarActions.style.display = 'none';
                fileInput.value = ''; 
                fetchFilesList(); // Refresh sidebar
            }
            else{
                showUploadError(result.message || "Upload failed.");
            }
        } catch (error) {
            alert("Upload failed.");
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = "Upload to Library";
        }
    };
}
// Helper to show errors nicely
function showUploadError(message) {
    // You can use a simple alert
    alert("⚠️ Duplicate Detected: " + message);
    
    // OR: Update the sidebar text to show the error in red
    const sidebarFileName = document.getElementById('sidebar-file-name');
    sidebarFileName.style.color = "#dc3545"; // Red color
    sidebarFileName.textContent = message;
}

// --- LIBRARY & SELECTION LOGIC ---
async function fetchFilesList() {
    try {
        const response = await fetch('/list-files');
        const files = await response.json();
        const list = document.getElementById('file-list');
        list.innerHTML = '';

        files.forEach(file => {
            const li = document.createElement('li');
            li.className = 'file-item';
            li.innerHTML = `
                        <span class="file-name-text" title="${file.original_name}">${file.original_name}</span>
                        <div class="file-actions">
                            <button class="text-btn download-btn" onclick="downloadFile('${file.file_id}')">
                                Download
                            </button>
                            <button class="text-btn delete-btn" onclick="deleteFile('${file.file_id}')">
                                Delete
                            </button>
                        </div>
                    `;
            
            // Selection logic (clicking the row, but not the buttons)
            li.onclick = (e) => {
                if (e.target.tagName !== 'BUTTON') {
                    selectFile(file.file_id, file.original_name, li);
                }
            };
            list.appendChild(li);
        });
    } catch (error) {
        console.error("Error loading library:", error);
    }
}

function selectFile(id, name, element) {
    currentFileId = id;
    
    // UI Switches
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('quiz-config-container').style.display = 'block';
    document.getElementById('quiz-container').style.display = 'none';
    
    // Update labels
    document.getElementById('status-text').textContent = "Ready to generate quiz";
    document.getElementById('active-file-display').textContent = `📄 ${name}`;
    
    // Highlight sidebar selection
    document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
}

// --- DOWNLOAD FUNCTION ---
function downloadFile(fileId) {
    // Direct browser redirect to the download API
    window.location.href = `/download-file/${fileId}`;
}

// --- DELETE FUNCTION ---
async function deleteFile(fileId) {
    if (!confirm("Are you sure you want to remove this file from your library?")) return;

    try {
        const response = await fetch(`/delete-file/${fileId}`, { method: 'DELETE' });
        if (response.ok) {
            // If we deleted the file currently being looked at, reset main view
            if (currentFileId === fileId) {
                currentFileId = null;
                document.getElementById('empty-state').style.display = 'block';
                document.getElementById('quiz-config-container').style.display = 'none';
                document.getElementById('status-text').textContent = "No content selected from library";
            }
            fetchFilesList(); // Refresh sidebar
        } else {
            alert("Delete failed.");
        }
    } catch (error) {
        alert("Error connecting to server.");
    }
}

// --- GENERATOR LOGIC ---
document.getElementById('generate-btn').onclick = async () => {
    if (!currentFileId) return alert("Select a file first");

    const btn = document.getElementById('generate-btn');
    btn.disabled = true;
    btn.textContent = "AI is thinking...";

    const formData = new FormData();
    formData.append('file_id', currentFileId);
    formData.append('mcq_count', document.getElementById('mcq-count').value);
    formData.append('subjective_count', document.getElementById('subjective-count').value);

    try {
        const response = await fetch('/generate-questions', { method: 'POST', body: formData });
        const result = await response.json();
        
        if (response.ok) {
            renderQuiz(result.quiz);
            document.getElementById('quiz-config-container').style.display = 'none';
            document.getElementById('quiz-container').style.display = 'block';
        }
    } catch (e) {
        alert("Generation Error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Generate Quiz";
    }
};

function renderQuiz(questions) {
    const list = document.getElementById('questions-list');
    list.innerHTML = '';
    questions.forEach((q, i) => {
        const div = document.createElement('div');
        div.className = 'question-item';
        div.innerHTML = `<h4>Q${i+1}: ${q.question}</h4>`;
        if(q.options) {
            q.options.forEach(opt => {
                div.innerHTML += `<label style="display:block; margin:5px 0;"><input type="radio" name="q${i}"> ${opt}</label>`;
            });
        } else {
            div.innerHTML += `<textarea style="width:100%; height:60px; margin-top:10px; padding:10px; border-radius:8px; border:1px solid #ddd;"></textarea>`;
        }
        list.appendChild(div);
    });
}