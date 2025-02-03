document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const activeTranslations = document.getElementById('activeTranslations');
    const historyTableBody = document.getElementById('historyTableBody');

    // Active jobs tracking
    const activeJobs = new Set();

    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData();
        const file = document.getElementById('file').files[0];
        const sourceLang = document.getElementById('sourceLang').value;
        const targetLang = document.getElementById('targetLang').value;

        formData.append('file', file);
        formData.append('source_language', sourceLang);
        formData.append('target_language', targetLang);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            
            if (response.ok) {
                showNotification('Translation job created successfully', 'success');
                activeJobs.add(data.job_id);
                uploadForm.reset();
                updateActiveTranslations();
            } else {
                showNotification(data.error, 'error');
            }
        } catch (error) {
            showNotification('Failed to upload document', 'error');
        }
    });

    function updateActiveTranslations() {
        activeTranslations.innerHTML = '';
        activeJobs.forEach(jobId => {
            const jobElement = createJobElement(jobId);
            activeTranslations.appendChild(jobElement);
            pollJobStatus(jobId);
        });
    }

    function createJobElement(jobId) {
        const div = document.createElement('div');
        div.className = 'translation-item';
        div.id = `job-${jobId}`;
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span>Job #${jobId}</span>
                <span class="status-badge status-pending">Pending</span>
            </div>
            <div class="progress">
                <div class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 0%" 
                     aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
            </div>
        `;
        return div;
    }

    async function pollJobStatus(jobId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/jobs/${jobId}/status`);
                const data = await response.json();
                
                updateJobStatus(jobId, data);
                
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(pollInterval);
                    activeJobs.delete(jobId);
                    await loadTranslationHistory();
                }
            } catch (error) {
                console.error('Error polling job status:', error);
            }
        }, 2000);
    }

    function updateJobStatus(jobId, data) {
        const jobElement = document.getElementById(`job-${jobId}`);
        if (!jobElement) return;

        const statusBadge = jobElement.querySelector('.status-badge');
        const progressBar = jobElement.querySelector('.progress-bar');

        statusBadge.className = `status-badge status-${data.status}`;
        statusBadge.textContent = data.status.charAt(0).toUpperCase() + data.status.slice(1);

        if (data.progress) {
            const progress = Math.round(data.progress);
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
            progressBar.textContent = `${progress}%`;
        }
    }

    async function loadTranslationHistory() {
        try {
            const response = await fetch('/api/jobs/history');
            const jobs = await response.json();
            
            historyTableBody.innerHTML = jobs.map(job => `
                <tr>
                    <td>${job.original_filename}</td>
                    <td>${job.source_language} → ${job.target_language}</td>
                    <td><span class="status-badge status-${job.status}">${job.status}</span></td>
                    <td>${new Date(job.created_at).toLocaleString()}</td>
                    <td>
                        ${job.status === 'completed' ? 
                            `<a href="/api/jobs/${job.id}/download" class="btn btn-sm btn-success btn-icon">
                                <i data-feather="download"></i> Download
                            </a>` : 
                            ''}
                    </td>
                </tr>
            `).join('');
            
            feather.replace();
        } catch (error) {
            console.error('Error loading translation history:', error);
        }
    }

    function showNotification(message, type) {
        // You could implement a toast notification here
        alert(message);
    }

    // Initial load
    loadTranslationHistory();
});
