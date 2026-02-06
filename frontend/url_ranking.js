// DOM Elements
const taskDescriptionEl = document.getElementById('taskDescription');
const urlInputEl = document.getElementById('urlInput');
const rankBtnEl = document.getElementById('rankBtn');
const loadingIndicatorEl = document.getElementById('loadingIndicator');
const resultsSectionEl = document.getElementById('resultsSection');
const errorMessageEl = document.getElementById('errorMessage');

// Main Ranking Function
rankBtnEl.addEventListener('click', async () => {
    // Validate inputs
    if (!taskDescriptionEl.value.trim()) {
        showError('请输入任务描述');
        return;
    }

    // Parse URLs from textarea (one per line)
    const urlText = urlInputEl.value.trim();
    if (!urlText) {
        showError('请输入至少 2 个 URL');
        return;
    }

    const urls = urlText
        .split('\n')
        .map(url => url.trim())
        .filter(url => url.length > 0);

    if (urls.length < 2) {
        showError('请输入至少 2 个 URL');
        return;
    }

    if (urls.length > 10) {
        showError('最多支持 10 个 URL');
        return;
    }

    // Validate URL format
    const invalidUrls = urls.filter(url => !isValidUrl(url));
    if (invalidUrls.length > 0) {
        showError(`以下 URL 格式不正确：\n${invalidUrls.join('\n')}`);
        return;
    }

    // Prepare request payload
    const payload = {
        task_description: taskDescriptionEl.value.trim(),
        urls: urls
    };

    // Show loading
    hideError();
    hideResults();
    showLoading();

    try {
        const response = await fetch('http://localhost:8000/api/v1/rank-urls', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || '请求失败');
        }

        const result = await response.json();
        displayResults(result);

    } catch (error) {
        showError(`分析失败: ${error.message}`);
    } finally {
        hideLoading();
    }
});

// Validate URL format
function isValidUrl(string) {
    try {
        const url = new URL(string);
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (_) {
        return false;
    }
}

// Display Results
function displayResults(result) {
    document.getElementById('bestChoice').textContent = result.best_candidate_id;
    document.getElementById('reasoning').textContent = result.reasoning;
    document.getElementById('processingTime').textContent = `${result.processing_time.toFixed(2)} 秒`;

    resultsSectionEl.style.display = 'block';
    resultsSectionEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// UI Helper Functions
function showLoading() {
    loadingIndicatorEl.style.display = 'block';
    rankBtnEl.disabled = true;
}

function hideLoading() {
    loadingIndicatorEl.style.display = 'none';
    rankBtnEl.disabled = false;
}

function showError(message) {
    errorMessageEl.textContent = message;
    errorMessageEl.style.display = 'block';
    errorMessageEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
    errorMessageEl.style.display = 'none';
}

function hideResults() {
    resultsSectionEl.style.display = 'none';
}
