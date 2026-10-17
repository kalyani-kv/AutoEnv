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

  const step1 = document.getElementById('step-1');
  const step2 = document.getElementById('step-2');

  const resultCard = document.getElementById('result-card');
  const resultProjectName = document.getElementById('result-project-name');
  const resultSessionId = document.getElementById('result-session-id');
  const statFileCount = document.getElementById('stat-file-count');
  const statTotalSize = document.getElementById('stat-total-size');
  const filesTree = document.getElementById('files-tree');
  const analyzeBtn = document.getElementById('analyze-btn');

  // Phase 2 Elements
  const analysisCard = document.getElementById('analysis-card');
  const situationTag = document.getElementById('situation-tag');
  const situationDescBox = document.getElementById('situation-description-box');
  const statPrimaryLang = document.getElementById('stat-primary-lang');
  const statExtCount = document.getElementById('stat-ext-count');
  const statStdlibCount = document.getElementById('stat-stdlib-count');
  const statLocalCount = document.getElementById('stat-local-count');
  const discrepancyCard = document.getElementById('discrepancy-card');
  const missingDepsList = document.getElementById('missing-deps-list');
  const missingDepsTags = document.getElementById('missing-deps-tags');
  const unusedDepsList = document.getElementById('unused-deps-list');
  const unusedDepsTags = document.getElementById('unused-deps-tags');
  const depTableBody = document.getElementById('dep-table-body');
  const stdlibPills = document.getElementById('stdlib-pills');
  const localPills = document.getElementById('local-pills');

  const errorCard = document.getElementById('error-card');
  const errorTitle = document.getElementById('error-title');
  const errorMessage = document.getElementById('error-message');
  const errorCategory = document.getElementById('error-category');

  let selectedFile = null;
  let currentSessionId = null;

  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

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

  // Phase 1: Upload & Extraction
  uploadBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    hideError();
    resultCard.classList.add('hidden');
    analysisCard.classList.add('hidden');
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

      progressBarFill.style.width = '100%';
      progressStatusText.textContent = 'Validation & Extraction Complete!';
      currentSessionId = data.session_id;

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

  // Phase 2: Static Language & Dependency Analysis
  if (analyzeBtn) {
    analyzeBtn.addEventListener('click', async () => {
      if (!currentSessionId) return;

      hideError();
      analyzeBtn.disabled = true;
      analyzeBtn.textContent = '⏳ Analyzing AST & Detecting Dependencies...';

      try {
        const response = await fetch(`/api/analyze/${currentSessionId}`, {
          method: 'POST',
        });

        const data = await response.json();

        if (!response.ok) {
          const errorDetail = data.detail || {};
          throw new Error(errorDetail.message || 'Analysis failed', { cause: errorDetail });
        }

        renderAnalysis(data);

        // Update stepper
        step1.classList.remove('active');
        step1.classList.add('completed');
        step2.classList.remove('disabled');
        step2.classList.add('active');

      } catch (err) {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = '🔍 Analyze Languages & Dependencies (Phase 2)';
        const detail = err.cause || {};
        showError(
          detail.error || 'Analysis Failed',
          err.message || 'Failed to analyze project dependencies.',
          detail.category || 'Analysis'
        );
      }
    });
  }

  function renderAnalysis(data) {
    const summary = data.summary || {};
    const py = data.python_analysis;

    statPrimaryLang.textContent = summary.primary_language || 'Unknown';
    statExtCount.textContent = summary.external_dependencies_count || 0;
    statStdlibCount.textContent = summary.stdlib_modules_count || 0;
    statLocalCount.textContent = summary.local_modules_count || 0;

    // Render Situation
    const sitCode = summary.situation || 'SITUATION_B';
    situationTag.className = 'situation-tag';
    if (sitCode === 'SITUATION_A') {
      situationTag.classList.add('situation-a');
      situationTag.textContent = 'Situation A: Manifest Complete';
    } else if (sitCode === 'SITUATION_C') {
      situationTag.classList.add('situation-c');
      situationTag.textContent = 'Situation C: Incomplete Manifest';
    } else {
      situationTag.classList.add('situation-b');
      situationTag.textContent = 'Situation B: Reconstructed from Code';
    }

    situationDescBox.textContent = summary.situation_description || 'Static analysis completed.';

    // Render Discrepancies if any
    if (py && (py.missing_from_manifest.length > 0 || py.unused_in_manifest.length > 0)) {
      discrepancyCard.classList.remove('hidden');

      if (py.missing_from_manifest.length > 0) {
        missingDepsList.classList.remove('hidden');
        missingDepsTags.innerHTML = py.missing_from_manifest
          .map(pkg => `<span class="tag tag-missing">${pkg}</span>`)
          .join('');
      } else {
        missingDepsList.classList.add('hidden');
      }

      if (py.unused_in_manifest.length > 0) {
        unusedDepsList.classList.remove('hidden');
        unusedDepsTags.innerHTML = py.unused_in_manifest
          .map(pkg => `<span class="tag tag-unused">${pkg}</span>`)
          .join('');
      } else {
        unusedDepsList.classList.add('hidden');
      }
    } else {
      discrepancyCard.classList.add('hidden');
    }

    // Render External Dependencies Table
    depTableBody.innerHTML = '';
    if (py && py.external_dependencies.length > 0) {
      py.external_dependencies.forEach(dep => {
        const row = document.createElement('tr');
        const isMissing = py.missing_from_manifest.includes(dep.name);

        const statusTag = isMissing
          ? '<span class="tag tag-missing">Missing from manifest</span>'
          : '<span class="tag tag-declared">Declared in manifest</span>';

        const sourcesFormatted = dep.source_files
          .map(f => `${f}`)
          .join(', ');

        row.innerHTML = `
          <td class="dep-name">${dep.name}</td>
          <td><span class="badge" style="background: rgba(6, 182, 212, 0.15); color: #22d3ee;">External</span></td>
          <td class="dep-version">${dep.version_spec || 'Latest / Undefined'}</td>
          <td class="dep-files">${sourcesFormatted} (lines: ${dep.line_numbers.join(', ')})</td>
          <td>${statusTag}</td>
        `;
        depTableBody.appendChild(row);
      });
    } else {
      depTableBody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No external dependencies discovered.</td></tr>';
    }

    // Render Standard Library Pills
    stdlibPills.innerHTML = '';
    if (py && py.standard_library_modules.length > 0) {
      py.standard_library_modules.forEach(mod => {
        const pill = document.createElement('span');
        pill.className = 'module-pill';
        pill.textContent = mod;
        stdlibPills.appendChild(pill);
      });
    } else {
      stdlibPills.innerHTML = '<span style="color: var(--text-muted); font-size: 0.8rem;">None detected</span>';
    }

    // Render Local Module Pills
    localPills.innerHTML = '';
    if (py && py.local_project_modules.length > 0) {
      py.local_project_modules.forEach(mod => {
        const pill = document.createElement('span');
        pill.className = 'module-pill';
        pill.textContent = mod;
        localPills.appendChild(pill);
      });
    } else {
      localPills.innerHTML = '<span style="color: var(--text-muted); font-size: 0.8rem;">None detected</span>';
    }

    analysisCard.classList.remove('hidden');
    analyzeBtn.textContent = '✓ Analysis Completed';
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
    currentSessionId = null;
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    resultCard.classList.add('hidden');
    analysisCard.classList.add('hidden');
    hideError();
    uploadBtn.classList.remove('hidden');
    uploadBtn.disabled = true;
    resetBtn.classList.add('hidden');
    if (analyzeBtn) {
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = '🔍 Analyze Languages & Dependencies (Phase 2)';
    }
    step1.classList.remove('completed');
    step1.classList.add('active');
    step2.classList.remove('active');
    step2.classList.add('disabled');
  });
});
