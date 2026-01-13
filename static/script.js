document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scan-btn');
    const targetInput = document.getElementById('target-input');
    const historyList = document.getElementById('history-list');
    const resultsArea = document.getElementById('results-area');
    const loader = document.querySelector('.loader');

    // Load history on startup
    loadHistory();

    scanBtn.addEventListener('click', async () => {
        const target = targetInput.value.trim();
        if (!target) return alert('Please enter a target!');

        // UI State: Scanning
        scanBtn.disabled = true;
        loader.style.display = 'inline-block';

        resultsArea.innerHTML = `
            <div class="result-card">
                <h3>Scan Status</h3>
                <div id="scan-summary-msg" style="margin-bottom: 1rem; font-weight: bold; color: var(--accent-color);">Initializing...</div>
                <div class="progress-container" style="display:block;"><div class="progress-bar"></div></div>
                <div id="status-log" class="status-log" style="display:block;"></div>
            </div>
            <div id="host-results-container"></div>
        `;

        const statusLog = document.getElementById('status-log');
        const summaryMsg = document.getElementById('scan-summary-msg');
        const hostResultsContainer = document.getElementById('host-results-container');
        let hostCount = 0;

        const addLog = (msg, isError = false) => {
            const div = document.createElement('div');
            div.className = `log-entry ${isError ? 'error' : ''}`;
            div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
            statusLog.appendChild(div);
            statusLog.scrollTop = statusLog.scrollHeight;
        };

        const appendHostResult = (host) => {
            hostCount++;
            summaryMsg.textContent = `Found ${hostCount} hosts so far...`;
            renderResultsIntoContainer(host, hostResultsContainer);
        };

        try {
            const response = await fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop(); // Keep incomplete chunk in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const payload = JSON.parse(line.substring(6));
                            if (payload.type === 'status') {
                                addLog(payload.message);
                                if (!payload.message.includes("Scanning")) {
                                    summaryMsg.textContent = payload.message;
                                }
                            } else if (payload.type === 'host_result') {
                                appendHostResult(payload.data);
                            } else if (payload.type === 'error') {
                                addLog(`Error: ${payload.message}`, true);
                                summaryMsg.textContent = "Scan encountered an error.";
                            }
                        } catch (e) { console.error("Parse error", e); }
                    }
                }
            }
            summaryMsg.innerHTML = `<span style="color:var(--success-color)">Scan Finished: Total ${hostCount} hosts discovered.</span>`;
            loadHistory(); // Refresh history sidebar after scan finishes
        } catch (error) {
            addLog(`Request Error: ${error.message}`, true);
        } finally {
            scanBtn.disabled = false;
            loader.style.display = 'none';
            // Hide progress bar when done
            const progress = document.querySelector('.progress-container');
            if (progress) progress.style.display = 'none';
        }
    });

    async function loadHistory() {
        try {
            const response = await fetch('/api/history');
            if (!response.ok) {
                const text = await response.text();
                console.error('History fetch failed:', text);
                return;
            }
            const history = await response.json();

            historyList.innerHTML = '';
            history.forEach(item => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.innerHTML = `
                    <div class="history-item-info">
                        <span class="target">${item.target}</span>
                        <span class="time">${item.timestamp}</span>
                    </div>
                    <button class="history-del-btn" title="Delete scan">&times;</button>
                `;

                // Clicking the info area renders the result
                div.querySelector('.history-item-info').onclick = (e) => {
                    renderResults(item.results, item.id);
                };

                // Clicking the delete button
                div.querySelector('.history-del-btn').onclick = async (e) => {
                    e.stopPropagation();
                    if (confirm(`Delete scan history for ${item.target}?`)) {
                        try {
                            const res = await fetch(`/api/history/${item.id}`, { method: 'DELETE' });
                            if (res.ok) {
                                div.remove();
                                // If the deleted scan was being viewed, clear results
                                resultsArea.innerHTML = '<div class="result-card"><p>Scan deleted.</p></div>';
                            }
                        } catch (err) { alert("Delete failed: " + err.message); }
                    }
                };

                historyList.appendChild(div);
            });
        } catch (e) {
            console.error('Error loading history:', e);
        }
    }

    function renderResultsIntoContainer(host, container, scanId = null) {
        const hostDiv = document.createElement('div');
        hostDiv.className = 'host-card-wrapper';
        hostDiv.innerHTML = getHostResultHTML(host, scanId);

        // Add toggle logic
        const header = hostDiv.querySelector('.host-card-header');
        header.onclick = () => {
            const card = hostDiv.querySelector('.result-card');
            card.classList.toggle('expanded');
        };

        container.appendChild(hostDiv);
    }

    function renderResults(hosts, scanId = null) {
        const hostList = Array.isArray(hosts) ? hosts : [hosts];

        // Clear previous results and logs
        resultsArea.innerHTML = `
            <div class="result-card" style="margin-bottom:1rem; border-color:var(--accent-color); display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h3 style="margin-top:0">Scan History Result</h3>
                    <p style="font-weight:bold; color:var(--success-color); margin-bottom:0;">Total ${hostList.length} hosts discovered in this scan.</p>
                </div>
                ${scanId ? `<a href="/api/export/csv/${scanId}" class="download-btn">Download Full CSV</a>` : ''}
            </div>
            <div id="host-results-container"></div>
        `;
        const container = document.getElementById('host-results-container');

        if (hostList.length === 0) {
            container.innerHTML = '<div class="result-card"><p>No data found for this scan.</p></div>';
            return;
        }

        hostList.forEach(host => {
            renderResultsIntoContainer(host, container, scanId);
        });
    }

    function getHostResultHTML(host, scanId = null) {
        if (!host) return '<div class="result-card"><p>No data found.</p></div>';

        let html = `
            <div class="result-card" style="margin-top: 1rem;">
                <div class="host-card-header">
                    <div>
                        <h3 style="margin:0;">Host: ${host.host} (${host.hostname || 'No Hostname'})</h3>
                        <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem;">Status: <span class="state-${host.state}">${host.state}</span></p>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span class="details-toggle-icon">▼</span>
                    </div>
                </div>
                
                <div class="host-details-content">
        `;

        if (!host.protocols || host.protocols.length === 0) {
            html += '<p>No open ports detected.</p>';
        } else {
            host.protocols.forEach(proto => {
                html += `
                    <h4>Protocol: ${proto.protocol}</h4>
                    <table class="port-table">
                        <thead>
                            <tr>
                                <th>Port</th>
                                <th>State</th>
                                <th>Service</th>
                                <th>Version</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                proto.ports.forEach(p => {
                    html += `
                        <tr>
                            <td>${p.port}</td>
                            <td class="state-${p.state}">${p.state}</td>
                            <td>${p.service}</td>
                            <td>${p.version}</td>
                        </tr>
                    `;
                });

                html += `</tbody></table>`;
            });
        }

        html += '</div></div>';
        return html;
    }
});
