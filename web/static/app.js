/**
 * Real-time Agent Dashboard
 * 
 * Handles WebSocket connection, agent state updates, and UI interactions.
 */

// WebSocket connection
let ws = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000;

// Agent state storage
const agents = new Map();

/**
 * Initialize the dashboard
 */
function init() {
    console.log('Initializing dashboard...');
    connectWebSocket();
}

/**
 * Connect to WebSocket server
 */
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/agents/ws`;
    
    updateConnectionStatus('connecting');
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    
    try {
        ws = new WebSocket(wsUrl);
        
        ws.onopen = handleWebSocketOpen;
        ws.onmessage = handleWebSocketMessage;
        ws.onerror = handleWebSocketError;
        ws.onclose = handleWebSocketClose;
    } catch (error) {
        console.error('Failed to create WebSocket:', error);
        scheduleReconnect();
    }
}

/**
 * Handle WebSocket connection opened
 */
function handleWebSocketOpen(event) {
    console.log('WebSocket connected');
    updateConnectionStatus('connected');
    reconnectAttempts = 0;
    
    // Send ping every 30 seconds to keep connection alive
    if (window.pingInterval) {
        clearInterval(window.pingInterval);
    }
    window.pingInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
}

/**
 * Handle incoming WebSocket messages
 */
function handleWebSocketMessage(event) {
    try {
        const message = JSON.parse(event.data);
        console.log('WebSocket message:', message);
        
        switch (message.type) {
            case 'snapshot':
                handleSnapshot(message);
                break;
            case 'agent_updated':
                handleAgentUpdate(message);
                break;
            case 'task_added':
                handleTaskAdded(message);
                break;
            case 'task_completed':
                handleTaskCompleted(message);
                break;
            case 'log_line':
                handleLogLine(message);
                break;
            case 'pong':
                // Keep-alive response
                break;
            default:
                console.warn('Unknown message type:', message.type);
        }
    } catch (error) {
        console.error('Error parsing WebSocket message:', error);
    }
}

/**
 * Handle WebSocket error
 */
function handleWebSocketError(event) {
    console.error('WebSocket error:', event);
    updateConnectionStatus('disconnected');
}

/**
 * Handle WebSocket connection closed
 */
function handleWebSocketClose(event) {
    console.log('WebSocket closed:', event.code, event.reason);
    updateConnectionStatus('disconnected');
    
    if (window.pingInterval) {
        clearInterval(window.pingInterval);
    }
    
    scheduleReconnect();
}

/**
 * Schedule a reconnection attempt
 */
function scheduleReconnect() {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        console.error('Max reconnection attempts reached');
        addLog('error', 'Connection lost. Please refresh the page.');
        return;
    }
    
    reconnectAttempts++;
    console.log(`Scheduling reconnect attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}...`);
    
    setTimeout(() => {
        connectWebSocket();
    }, RECONNECT_DELAY);
}

/**
 * Update connection status indicator
 */
function updateConnectionStatus(status) {
    const statusEl = document.getElementById('connectionStatus');
    const statusText = document.getElementById('statusText');
    
    statusEl.className = 'connection-status';
    
    switch (status) {
        case 'connected':
            statusEl.classList.add('connection-connected');
            statusText.textContent = '● Connected';
            break;
        case 'connecting':
            statusEl.classList.add('connection-connecting');
            statusText.textContent = '◐ Connecting...';
            break;
        case 'disconnected':
            statusEl.classList.add('connection-disconnected');
            statusText.textContent = '○ Disconnected';
            break;
    }
}

/**
 * Handle snapshot message (initial state)
 */
function handleSnapshot(message) {
    console.log('Received snapshot with', message.agents.length, 'agents');
    
    // Clear and update agents
    agents.clear();
    message.agents.forEach(agent => {
        agents.set(agent.id, agent);
    });
    
    renderAgentTable();
    updateMetrics();
    addLog('info', `Dashboard initialized with ${message.agents.length} agents`);
}

/**
 * Handle agent update message
 */
function handleAgentUpdate(message) {
    const agent = message.agent;
    agents.set(agent.id, agent);
    
    renderAgentTable();
    updateMetrics();
    addLog('info', `Agent ${agent.id} updated: ${agent.status}`);
}

/**
 * Handle task added message
 */
function handleTaskAdded(message) {
    const agent = agents.get(message.agent_id);
    if (agent) {
        agent.tasks_pending = (agent.tasks_pending || 0) + 1;
        agents.set(message.agent_id, agent);
        renderAgentTable();
        updateMetrics();
    }
    addLog('info', `Task added to ${message.agent_id}: ${message.task.description}`);
}

/**
 * Handle task completed message
 */
function handleTaskCompleted(message) {
    const agent = agents.get(message.agent_id);
    if (agent) {
        agent.tasks_pending = Math.max(0, (agent.tasks_pending || 0) - 1);
        if (message.success) {
            agent.tasks_completed = (agent.tasks_completed || 0) + 1;
        } else {
            agent.tasks_failed = (agent.tasks_failed || 0) + 1;
        }
        agents.set(message.agent_id, agent);
        renderAgentTable();
        updateMetrics();
    }
    const status = message.success ? 'completed' : 'failed';
    addLog(message.success ? 'info' : 'error', 
           `Task ${status} on ${message.agent_id}: ${message.task_id}`);
}

/**
 * Handle log line message
 */
function handleLogLine(message) {
    addLog(message.level, `[${message.agent_id}] ${message.message}`);
}

/**
 * Render the agent table
 */
function renderAgentTable() {
    const tbody = document.getElementById('agentTableBody');
    
    if (agents.size === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted">
                    No agents available
                </td>
            </tr>
        `;
        return;
    }
    
    const rows = Array.from(agents.values()).map(agent => {
        const statusClass = `status-${agent.status}`;
        const uptimeFormatted = formatUptime(agent.uptime_seconds);
        
        return `
            <tr data-agent-id="${agent.id}">
                <td><code>${agent.id}</code></td>
                <td>${agent.name}</td>
                <td><span class="status-badge ${statusClass}">${agent.status}</span></td>
                <td>${agent.current_task || '<span class="text-muted">-</span>'}</td>
                <td>${agent.tasks_pending || 0}</td>
                <td>${agent.tasks_completed || 0}</td>
                <td>${agent.tasks_failed || 0}</td>
                <td>${uptimeFormatted}</td>
                <td>
                    ${renderActionButtons(agent)}
                </td>
            </tr>
        `;
    }).join('');
    
    tbody.innerHTML = rows;
}

/**
 * Render action buttons for an agent
 */
function renderActionButtons(agent) {
    const buttons = [];
    
    if (agent.status === 'running') {
        buttons.push(`<button class="btn btn-warning btn-sm action-btn" onclick="executeAction('${agent.id}', 'pause')">Pause</button>`);
        buttons.push(`<button class="btn btn-danger btn-sm action-btn" onclick="executeAction('${agent.id}', 'stop')">Stop</button>`);
    } else if (agent.status === 'paused') {
        buttons.push(`<button class="btn btn-success btn-sm action-btn" onclick="executeAction('${agent.id}', 'resume')">Resume</button>`);
        buttons.push(`<button class="btn btn-danger btn-sm action-btn" onclick="executeAction('${agent.id}', 'stop')">Stop</button>`);
    } else if (agent.status === 'stopped' || agent.status === 'idle') {
        buttons.push(`<button class="btn btn-primary btn-sm action-btn" onclick="executeAction('${agent.id}', 'restart')">Start</button>`);
    }
    
    return buttons.join(' ');
}

/**
 * Execute an action on an agent
 */
async function executeAction(agentId, action) {
    console.log(`Executing action ${action} on agent ${agentId}`);
    
    try {
        const response = await fetch(`/api/agents/${agentId}/action`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Action failed');
        }
        
        const result = await response.json();
        console.log('Action result:', result);
        addLog('info', result.message);
    } catch (error) {
        console.error('Action failed:', error);
        addLog('error', `Action failed: ${error.message}`);
        alert(`Failed to execute action: ${error.message}`);
    }
}

/**
 * Update metrics summary
 */
function updateMetrics() {
    const totalAgents = agents.size;
    const activeAgents = Array.from(agents.values()).filter(a => a.status === 'running').length;
    const tasksPending = Array.from(agents.values()).reduce((sum, a) => sum + (a.tasks_pending || 0), 0);
    const tasksCompleted = Array.from(agents.values()).reduce((sum, a) => sum + (a.tasks_completed || 0), 0);
    
    document.getElementById('metricTotalAgents').textContent = totalAgents;
    document.getElementById('metricActiveAgents').textContent = activeAgents;
    document.getElementById('metricTasksPending').textContent = tasksPending;
    document.getElementById('metricTasksCompleted').textContent = tasksCompleted;
}

/**
 * Add a log entry to the log panel
 */
function addLog(level, message) {
    const logContent = document.getElementById('logContent');
    const timestamp = new Date().toLocaleTimeString();
    
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    
    const levelClass = `log-${level}`;
    logEntry.innerHTML = `
        <span class="log-timestamp">[${timestamp}]</span>
        <span class="${levelClass}">[${level.toUpperCase()}]</span>
        ${escapeHtml(message)}
    `;
    
    logContent.appendChild(logEntry);
    
    // Auto-scroll to bottom
    const logPanel = document.getElementById('logPanel');
    logPanel.scrollTop = logPanel.scrollHeight;
    
    // Keep only last 100 log entries
    while (logContent.children.length > 100) {
        logContent.removeChild(logContent.firstChild);
    }
}

/**
 * Clear log panel
 */
function clearLogs() {
    document.getElementById('logContent').innerHTML = '';
}

/**
 * Refresh agents manually
 */
async function refreshAgents() {
    try {
        const response = await fetch('/api/agents');
        const agentsList = await response.json();
        
        agents.clear();
        agentsList.forEach(agent => {
            agents.set(agent.id, agent);
        });
        
        renderAgentTable();
        updateMetrics();
        addLog('info', 'Agents refreshed manually');
    } catch (error) {
        console.error('Failed to refresh agents:', error);
        addLog('error', 'Failed to refresh agents');
    }
}

/**
 * Format uptime in human-readable format
 */
function formatUptime(seconds) {
    if (!seconds || seconds === 0) return '-';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
        return `${minutes}m ${secs}s`;
    } else {
        return `${secs}s`;
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
