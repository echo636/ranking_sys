// State Management
const state = {
    candidates: [],
    scenarios: [],
    results: null,
    sessionId: 'sess_' + Date.now()
};

// DOM Elements
const steps = ['step1', 'step2', 'step3', 'step4'];
const candidatesContainer = document.getElementById('candidatesContainer');
const scenariosList = document.getElementById('scenariosList');
const resultTableBody = document.getElementById('resultTableBody');

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    // Add 2 default empty candidate inputs
    addCandidateInput();
    addCandidateInput();

    // Bind Events
    document.getElementById('addCandidateBtn').addEventListener('click', addCandidateInput);
    document.getElementById('goToStep2Btn').addEventListener('click', handleStep1Submit);
    document.getElementById('generateBtn').addEventListener('click', generateScenarios);
    document.getElementById('goToStep3Btn').addEventListener('click', () => switchStep(3));
    document.getElementById('startTestBtn').addEventListener('click', startBatchTest);

    // Back buttons
    document.querySelectorAll('.back-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const target = e.target.dataset.target;
            const stepNum = parseInt(target.replace('step', ''));
            switchStep(stepNum);
        });
    });
});

// --- Step 1: Candidates ---

function addCandidateInput() {
    if (candidatesContainer.children.length >= 5) {
        alert('鏈€澶氭敮鎸?5 涓€欓€夐」');
        return;
    }

    const template = document.getElementById('candidateTemplate');
    const clone = template.content.cloneNode(true);

    // Bind delete button
    clone.querySelector('.btn-remove').addEventListener('click', (e) => {
        if (candidatesContainer.children.length <= 2) {
            alert('鑷冲皯闇€瑕?2 涓€欓€夐」');
            return;
        }
        e.target.closest('.candidate-input-group').remove();
    });

    candidatesContainer.appendChild(clone);
}

function handleStep1Submit() {
    const inputs = candidatesContainer.querySelectorAll('.candidate-input-group');
    const candidates = [];

    inputs.forEach((div, index) => {
        const name = div.querySelector('.candidate-name').value.trim();
        const desc = div.querySelector('.candidate-desc').value.trim();

        if (name && desc) {
            candidates.push({
                id: `cand_${index + 1}`,
                name: name,
                info: {
                    category: "General",
                    description: desc
                }
            });
        }
    });

    if (candidates.length < 2) {
        alert('璇疯嚦灏戝～鍐?2 涓畬鏁寸殑鍊欓€夐」淇℃伅');
        return;
    }

    state.candidates = candidates;
    switchStep(2);

    // Auto generate if empty
    if (state.scenarios.length === 0) {
        generateScenarios();
    }
}

// --- Step 2: Scenarios ---

async function generateScenarios() {
    const generateBtn = document.getElementById('generateBtn');
    const statusDiv = document.getElementById('generationStatus');
    const nextBtn = document.getElementById('goToStep3Btn');

    generateBtn.disabled = true;
    nextBtn.style.display = 'none';
    scenariosList.innerHTML = '';
    statusDiv.style.display = 'block';

    try {
        const count = document.getElementById('scenarioCount').value;

        const response = await fetch('http://localhost:8000/api/v1/batch/generate-scenarios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidates: state.candidates,
                num_scenarios: parseInt(count)
            })
        });

        if (!response.ok) throw new Error('Generation failed');

        const data = await response.json();
        state.scenarios = data.scenarios;

        renderScenarios();
        nextBtn.style.display = 'inline-block';

    } catch (error) {
        alert('鍦烘櫙鐢熸垚澶辫触: ' + error.message);
    } finally {
        generateBtn.disabled = false;
        statusDiv.style.display = 'none';
    }
}

function renderScenarios() {
    scenariosList.innerHTML = state.scenarios.map((s, i) => `
        <div class="scenario-card">
            <h4>场景 ${i + 1}</h4>
            <p>${s.description}</p>
        </div>
    `).join('');
}

// --- Step 3: Test Execution ---

async function startBatchTest() {
    const startBtn = document.getElementById('startTestBtn');
    startBtn.style.display = 'none';

    // 鍒濆鍖栬繘搴︽樉绀轰负 0
    updateProgress({ current: 0, total: state.scenarios.length, percentage: 0 });

    // 鍏堝缓绔?WebSocket 杩炴帴
    const ws = new WebSocket(`ws://localhost:8000/api/v1/batch/ws/progress/${state.sessionId}`);

    // 绛夊緟 WebSocket 杩炴帴鎴愬姛
    await new Promise((resolve, reject) => {
        ws.onopen = () => {
            console.log('WebSocket connected');
            resolve();
        };
        ws.onerror = (error) => {
            console.error('WebSocket connection error:', error);
            reject(error);
        };
        // 瓒呮椂淇濇姢
        setTimeout(() => resolve(), 2000);
    });


    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateProgress(data);

        // Log to live view
        const logs = document.getElementById('liveLogs');
        const logItem = document.createElement('div');
        logItem.className = 'log-item';
        logItem.textContent = `[${new Date().toLocaleTimeString()}] 完成测试场景 ${data.current}/${data.total}`;
        logs.prepend(logItem);
    };

    try {
        // Prepare the payload according to API expectation
        // API expects {candidates: [...], scenarios: [...]} in body
        const payload = {
            candidates: state.candidates,
            scenarios: state.scenarios
        };

        const response = await fetch(`http://localhost:8000/api/v1/batch/start-tests?session_id=${state.sessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.ok) throw new Error('Batch test failed');

        const result = await response.json();
        state.results = result;

        ws.close();
        switchStep(4);
        renderResults();

    } catch (error) {
        alert('娴嬭瘯鎵ц澶辫触: ' + error.message);
        ws.close();
        startBtn.style.display = 'inline-block';
    }
}

function updateProgress(data) {
    const fill = document.getElementById('progressBarFill');
    const text = document.getElementById('progressText');

    fill.style.width = `${data.percentage}%`;
    text.textContent = `${data.current} / ${data.total} (${data.percentage}%)`;
}

// --- Step 4: Results ---

function renderResults() {
    const { total_tests, results, win_rate, scenario_details } = state.results;

    // Stats
    document.getElementById('totalTestsVal').textContent = total_tests;

    // Determine winner
    let maxWins = -1;
    let winner = '骞冲眬';
    for (const [candId, count] of Object.entries(results)) {
        if (count > maxWins) {
            maxWins = count;
            // Find name
            const cand = state.candidates.find(c => c.id === candId);
            winner = cand ? cand.name : candId;
        }
    }
    document.getElementById('winnerVal').textContent = winner;

    // Chart
    renderChart(win_rate);

    // Table
    resultTableBody.innerHTML = scenario_details.map((detail, i) => {
        const winnerCand = state.candidates.find(c => c.id === detail.winner_id);
        const winnerName = winnerCand ? winnerCand.name : detail.winner_id;

        return `
            <tr>
                <td>${i + 1}</td>
                <td>${detail.scenario_description}</td>
                <td><span class="win-tag">${winnerName}</span></td>
                <td style="font-size: 0.9rem; color: #4a5568;">${detail.reasoning.substring(0, 150)}...</td>
            </tr>
        `;
    }).join('');
}

function renderChart(winRates) {
    const ctx = document.getElementById('winRateChart').getContext('2d');
    const labels = Object.keys(winRates).map(id => {
        const cand = state.candidates.find(c => c.id === id);
        return cand ? cand.name : id;
    });

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '胜率',
                data: Object.values(winRates).map(v => (v * 100).toFixed(1)),
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { callback: v => v + '%' }
                }
            }
        }
    });
}

// --- Utility ---

function switchStep(stepNum) {
    // Nav
    document.querySelectorAll('.step-item').forEach((el, i) => {
        if (i + 1 < stepNum) el.className = 'step-item completed';
        else if (i + 1 === stepNum) el.className = 'step-item active';
        else el.className = 'step-item';
    });

    // Content
    document.querySelectorAll('section').forEach(el => el.classList.remove('active'));
    document.getElementById(`step${stepNum}`).classList.add('active');
}
