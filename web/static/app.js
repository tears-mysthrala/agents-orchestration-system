/**
 * Real-time Agent Dashboard
 * 
 * Handles WebSocket connections and agent management UI
 * Compatible with modern browsers on Windows and Linux
 */

class AgentDashboard {
    constructor() {
        this.ws = null;
        this.agents = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.logs = [];
        this.maxLogs = 100;
        
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.startPingInterval();
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/agents/ws`;
        
        this.updateConnectionStatus('connecting');
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.updateConnectionStatus('connected');
                this.reconnectAttempts = 0;
                this.addLog('info', 'Connected to server');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Error parsing message:', error);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.addLog('error', 'Connection error occurred');
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateConnectionStatus('disconnected');
                this.addLog('warn', 'Disconnected from server');
                this.attemptReconnect();
            };
        } catch (error) {
            console.error('Error creating WebSocket:', error);
            this.updateConnectionStatus('disconnected');
            this.attemptReconnect();
        }
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * this.reconnectAttempts;
            
            this.addLog('info', `Reconnecting in ${delay/1000}s... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connectWebSocket();
            }, delay);
        } else {
            this.addLog('error', 'Max reconnection attempts reached. Please refresh the page.');
        }
    }
    
    startPingInterval() {
        // Send ping every 30 seconds to keep connection alive
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }
    
    handleMessage(message) {
        switch (message.type) {
            case 'snapshot':
                this.handleSnapshot(message.data);
                break;
            case 'agent_updated':
                this.handleAgentUpdate(message.data);
                break;
            case 'task_added':
                this.handleTaskAdded(message.data);
                break;
            case 'task_completed':
                this.handleTaskCompleted(message.data);
                break;
            case 'log_line':
                this.handleLogLine(message.data);
                break;
            case 'pong':
                // Pong received, connection is alive
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
    }
    
    handleSnapshot(agentsData) {
        console.log('Received snapshot with', agentsData.length, 'agents');
        this.agents.clear();
        
        agentsData.forEach(agent => {
            this.agents.set(agent.id, agent);
        });
        
        this.renderAgentsTable();
        this.addLog('info', `Loaded ${agentsData.length} agents`);
    }
    
    handleAgentUpdate(agentData) {
        console.log('Agent updated:', agentData.id);
        this.agents.set(agentData.id, agentData);
        this.renderAgentsTable();
        this.addLog('info', `Agent ${agentData.name} updated: ${agentData.status}`);
    }
    
    handleTaskAdded(data) {
        console.log('Task added:', data);
        this.addLog('info', `Task added to ${data.agent_id}: ${data.task}`);
    }
    
    handleTaskCompleted(data) {
        console.log('Task completed:', data);
        this.addLog('info', `Task completed by ${data.agent_id}: ${data.task}`);
    }
    
    handleLogLine(data) {
        console.log('Log line:', data);
        this.addLog(data.level || 'info', `[${data.agent_id}] ${data.message}`);
    }
    
    renderAgentsTable() {
        const tbody = document.getElementById('agentsTableBody');
        
        if (this.agents.size === 0) {
            tbody.innerHTML = `
                <tr class="empty-state">
                    <td colspan="8">
                        <div class="empty-state">
                            <p style="font-size: 1.2em;">No agents found</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        // Clear existing content
        tbody.innerHTML = '';
        
        Array.from(this.agents.values()).forEach(agent => {
            const row = document.createElement('tr');
            row.className = 'updating';
            row.dataset.agentId = agent.id;
            
            const statusClass = `status-${agent.status}`;
            const canPause = agent.status === 'running';
            const canResume = agent.status === 'paused';
            const canStop = agent.status !== 'stopped';
            
            // Create cells with text content (XSS-safe)
            const idCell = document.createElement('td');
            const idStrong = document.createElement('strong');
            idStrong.textContent = agent.id;
            idCell.appendChild(idStrong);
            
            const nameCell = document.createElement('td');
            nameCell.textContent = agent.name;
            
            const typeCell = document.createElement('td');
            typeCell.textContent = agent.type;
            
            const statusCell = document.createElement('td');
            const statusSpan = document.createElement('span');
            statusSpan.className = `agent-status ${statusClass}`;
            statusSpan.textContent = agent.status;
            statusCell.appendChild(statusSpan);
            
            const taskCell = document.createElement('td');
            if (agent.current_task) {
                taskCell.textContent = agent.current_task;
            } else {
                const em = document.createElement('em');
                em.style.color = '#94a3b8';
                em.textContent = 'No task';
                taskCell.appendChild(em);
            }
            
            const completedCell = document.createElement('td');
            completedCell.textContent = agent.tasks_completed;
            
            const pendingCell = document.createElement('td');
            pendingCell.textContent = agent.tasks_pending;
            
            // Create actions cell with event listeners (XSS-safe)
            const actionsCell = document.createElement('td');
            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'actions';
            
            const pauseBtn = this.createActionButton('Pause', 'btn-pause', !canPause, () => this.executeAction(agent.id, 'pause'));
            const resumeBtn = this.createActionButton('Resume', 'btn-resume', !canResume, () => this.executeAction(agent.id, 'resume'));
            const stopBtn = this.createActionButton('Stop', 'btn-stop', !canStop, () => this.executeAction(agent.id, 'stop'));
            const restartBtn = this.createActionButton('Restart', 'btn-restart', false, () => this.executeAction(agent.id, 'restart'));
            const prioritizeBtn = this.createActionButton('Prioritize', 'btn-prioritize', false, () => this.executeAction(agent.id, 'prioritize', {priority: 'high'}));
            
            actionsDiv.append(pauseBtn, resumeBtn, stopBtn, restartBtn, prioritizeBtn);
            actionsCell.appendChild(actionsDiv);
            
            row.append(idCell, nameCell, typeCell, statusCell, taskCell, completedCell, pendingCell, actionsCell);
            tbody.appendChild(row);
        });
        
        // Remove animation class after animation completes
        setTimeout(() => {
            document.querySelectorAll('.updating').forEach(el => {
                el.classList.remove('updating');
            });
        }, 1000);
    }
    
    createActionButton(text, className, disabled, onClick) {
        const btn = document.createElement('button');
        btn.className = `btn ${className}`;
        btn.textContent = text;
        btn.disabled = disabled;
        if (!disabled) {
            btn.addEventListener('click', onClick);
        }
        return btn;
    }
    
    async executeAction(agentId, action, parameters = {}) {
        try {
            const response = await fetch(`/api/agents/${agentId}/action`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: action,
                    parameters: parameters
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Action failed');
            }
            
            const result = await response.json();
            console.log('Action result:', result);
            this.addLog('info', result.message);
        } catch (error) {
            console.error('Error executing action:', error);
            this.addLog('error', `Failed to execute ${action}: ${error.message}`);
            alert(`Error: ${error.message}`);
        }
    }
    
    addLog(level, message) {
        const timestamp = new Date().toLocaleTimeString();
        const log = { timestamp, level, message };
        
        this.logs.unshift(log);
        if (this.logs.length > this.maxLogs) {
            this.logs.pop();
        }
        
        this.renderLogs();
    }
    
    renderLogs() {
        const container = document.getElementById('logsContainer');
        
        if (this.logs.length === 0) {
            container.innerHTML = `
                <div style="color: #94a3b8; text-align: center; padding: 20px;">
                    Activity logs will appear here...
                </div>
            `;
            return;
        }
        
        // Clear and rebuild with XSS-safe DOM manipulation
        container.innerHTML = '';
        
        this.logs.forEach(log => {
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            
            const timestamp = document.createElement('span');
            timestamp.className = 'log-timestamp';
            timestamp.textContent = log.timestamp;
            
            const level = document.createElement('span');
            level.className = `log-level-${log.level}`;
            level.textContent = `[${log.level.toUpperCase()}]`;
            
            const message = document.createElement('span');
            message.className = 'log-message';
            message.textContent = log.message;
            
            entry.append(timestamp, level, message);
            container.appendChild(entry);
        });
    }
    
    updateConnectionStatus(status) {
        const statusEl = document.getElementById('connectionStatus');
        statusEl.className = 'connection-status';
        
        switch (status) {
            case 'connected':
                statusEl.classList.add('status-connected');
                statusEl.textContent = '🟢 Connected';
                break;
            case 'disconnected':
                statusEl.classList.add('status-disconnected');
                statusEl.textContent = '🔴 Disconnected';
                break;
            case 'connecting':
                statusEl.classList.add('status-connecting');
                statusEl.textContent = '🟡 Connecting...';
                break;
        }
    }
    
    setupEventListeners() {
        // Handle page visibility changes (reconnect when tab becomes visible)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && (!this.ws || this.ws.readyState !== WebSocket.OPEN)) {
                this.reconnectAttempts = 0;
                this.connectWebSocket();
            }
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (this.ws) {
                this.ws.close();
            }
        });
    }
}

// Initialize dashboard when DOM is ready
let dashboard;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        dashboard = new AgentDashboard();
    });
} else {
    dashboard = new AgentDashboard();
}
