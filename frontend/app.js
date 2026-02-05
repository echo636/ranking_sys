// State Management
let candidates = [];
let candidateIdCounter = 1;

// DOM Elements
const taskDescriptionEl = document.getElementById('taskDescription');
const candidatesListEl = document.getElementById('candidatesList');
const addCandidateBtnEl = document.getElementById('addCandidateBtn');
const rankBtnEl = document.getElementById('rankBtn');
const loadingIndicatorEl = document.getElementById('loadingIndicator');
const resultsSectionEl = document.getElementById('resultsSection');
const errorMessageEl = document.getElementById('errorMessage');

// Initialize with one candidate
document.addEventListener('DOMContentLoaded', () => {
    addCandidate();
});

// Add Candidate
addCandidateBtnEl.addEventListener('click', () => {
    addCandidate();
});

function addCandidate() {
    const candidate = {
        id: `item_${candidateIdCounter++}`,
        name: '',
        category: '',
        price: '',
        description: ''
    };

    candidates.push(candidate);
    renderCandidates();
}

// Remove Candidate
function removeCandidate(index) {
    candidates.splice(index, 1);
    renderCandidates();
}

// Render Candidates
function renderCandidates() {
    candidatesListEl.innerHTML = '';

    if (candidates.length === 0) {
        candidatesListEl.innerHTML = '<p style="text-align: center; color: #999;">暂无候选项，点击上方按钮添加</p>';
        return;
    }

    candidates.forEach((candidate, index) => {
        const candidateEl = document.createElement('div');
        candidateEl.className = 'candidate-item';
        candidateEl.innerHTML = `
            <div class="candidate-header">
                <div class="candidate-number">${index + 1}</div>
                <button class="btn btn-danger" onclick="removeCandidate(${index})">删除</button>
            </div>
            
            <div class="form-group" style="margin-bottom: 10px;">
                <label>候选项名称 *</label>
                <input type="text" 
                       placeholder="例如：JBL Go 3 蓝牙音箱" 
                       value="${candidate.name}"
                       onchange="updateCandidate(${index}, 'name', this.value)">
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>类别</label>
                    <input type="text" 
                           placeholder="例如：电子产品" 
                           value="${candidate.category}"
                           onchange="updateCandidate(${index}, 'category', this.value)">
                </div>
                <div class="form-group">
                    <label>价格 (CNY)</label>
                    <input type="number" 
                           placeholder="299" 
                           value="${candidate.price}"
                           onchange="updateCandidate(${index}, 'price', this.value)">
                </div>
            </div>
            
            <div class="form-group">
                <label>详细描述</label>
                <textarea 
                    placeholder="描述商品/服务的特点、优势等..." 
                    rows="2"
                    onchange="updateCandidate(${index}, 'description', this.value)">${candidate.description}</textarea>
            </div>
        `;

        candidatesListEl.appendChild(candidateEl);
    });
}

// Update Candidate Data
function updateCandidate(index, field, value) {
    candidates[index][field] = value;
}

// Main Ranking Function
rankBtnEl.addEventListener('click', async () => {
    // Validate inputs
    if (!taskDescriptionEl.value.trim()) {
        showError('请输入任务描述');
        return;
    }

    if (candidates.length === 0) {
        showError('请至少添加一个候选项');
        return;
    }

    // Check if all candidates have names
    const invalidCandidates = candidates.filter(c => !c.name.trim());
    if (invalidCandidates.length > 0) {
        showError('所有候选项都必须填写名称');
        return;
    }

    // Prepare request payload
    const payload = {
        task_description: taskDescriptionEl.value.trim(),
        candidates: candidates.map(c => ({
            id: c.id,
            name: c.name.trim(),
            info: {
                category: c.category.trim() || undefined,
                price: c.price ? parseFloat(c.price) : undefined,
                currency: "CNY",
                description: c.description.trim() || undefined
            }
        }))
    };

    // Show loading
    hideError();
    hideResults();
    showLoading();

    try {
        const response = await fetch('http://localhost:8000/api/v1/rank', {
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

// Display Results
function displayResults(result) {
    const bestCandidate = candidates.find(c => c.id === result.best_candidate_id);
    const bestCandidateName = bestCandidate ? bestCandidate.name : result.best_candidate_id;

    document.getElementById('bestChoice').textContent = bestCandidateName;
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
