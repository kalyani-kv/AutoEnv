document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');
  const fileInfo = document.getElementById('file-info');
  const fileName = document.getElementById('file-name');
  const fileSize = document.getElementById('file-size');
  const uploadBtn = document.getElementById('upload-btn');
  const resetBtn = document.getElementById('reset-btn');
  const progressContainer = document.getElementById('progress-container');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressStatusText = document.getElementById('progress-status-text');

  const resultCard = document.getElementById('result-card');
  const resultProjectName = document.getElementById('result-project-name');
  const resultSessionId = document.getElementById('result-session-id');
  const statFileCount = document.getElementById('stat-file-count');
  const statTotalSize = document.getElementById('stat-total-size');
  const filesTree = document.getElementById('files-tree');

  const errorCard = document.getElementById('error-card');
  const errorTitle = document.getElementById('error-title');
  const errorMessage = document.getElementById('error-message');
  const errorCategory = document.getElementById('error-category');

  let selectedFile = null;

  // File size formatter
  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // File Selection
  function handleFileSelection(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.zip')) {
      showError('Invalid File Type', 'Please select a valid .zip archive file.', 'FileValidation');
      return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = `(${formatBytes(file.size)})`;
    fileInfo.classList.remove('hidden');
    uploadBtn.disabled = false;
    hideError();
  }

  // Drag & Drop Events
  dropZone.addEventListener('click', () => fileInput.click());

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileSelection(e.target.files[0]);
    }
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFileSelection(e.dataTransfer.files[0]);
    }
  });

  // Upload & Extraction Handler
  uploadBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    // Reset UI state
    hideError();
    resultCard.classList.add('hidden');
    uploadBtn.disabled = true;
    progressContainer.classList.remove('hidden');
    progressBarFill.style.width = '30%';
    progressStatusText.textContent = 'Uploading project archive...';

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      progressBarFill.style.width = '65%';
      progressStatusText.textContent = 'Validating ZipSlip & decompression thresholds...';

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        const errorDetail = data.detail || {};
        throw new Error(errorDetail.message || 'Archive validation or extraction failed', {
          cause: errorDetail,
        });
      }

      // Success
      progressBarFill.style.width = '100%';
      progressStatusText.textContent = 'Validation & Extraction Complete!';

      setTimeout(() => {
        progressContainer.classList.add('hidden');
        showResult(data);
      }, 400);

    } catch (err) {
      progressContainer.classList.add('hidden');
      uploadBtn.disabled = false;
      const detail = err.cause || {};
      showError(
        detail.error || 'Extraction Failed',
        err.message || 'An unexpected error occurred during processing.',
        detail.category || 'System'
      );
    }
  });

  function showResult(data) {
    resultProjectName.textContent = data.project_name;
    resultSessionId.textContent = data.session_id;
    statFileCount.textContent = data.extracted_file_count;
    statTotalSize.textContent = formatBytes(data.total_size_bytes);

    // Populate file tree
    filesTree.innerHTML = '';
    data.files.forEach(file => {
      const item = document.createElement('div');
      item.className = 'tree-item';
      item.textContent = `📄 ${file}`;
      filesTree.appendChild(item);
    });

    resultCard.classList.remove('hidden');
    resetBtn.classList.remove('hidden');
    uploadBtn.classList.add('hidden');
  }

  function showError(title, message, category) {
    errorTitle.textContent = title;
    errorMessage.textContent = message;
    errorCategory.textContent = category;
    errorCard.classList.remove('hidden');
  }

  function hideError() {
    errorCard.classList.add('hidden');
  }

  resetBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    resultCard.classList.add('hidden');
    hideError();
    uploadBtn.classList.remove('hidden');
    uploadBtn.disabled = true;
    resetBtn.classList.add('hidden');
  });
});
