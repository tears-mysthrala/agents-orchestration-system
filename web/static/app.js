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
        
        const rows = Array.from(this.agents.values()).map(agent => {
            const statusClass = `status-${agent.status}`;
            const canPause = agent.status === 'running';
            const canResume = agent.status === 'paused';
            const canStop = agent.status !== 'stopped';
            
            return `
                <tr class="updating" data-agent-id="${agent.id}">
                    <td><strong>${agent.id}</strong></td>
                    <td>${agent.name}</td>
                    <td>${agent.type}</td>
                    <td><span class="agent-status ${statusClass}">${agent.status}</span></td>
                    <td>${agent.current_task || '<em style="color: #94a3b8;">No task</em>'}</td>
                    <td>${agent.tasks_completed}</td>
                    <td>${agent.tasks_pending}</td>
                    <td>
                        <div class="actions">
                            <button class="btn btn-pause" onclick="dashboard.executeAction('${agent.id}', 'pause')" ${!canPause ? 'disabled' : ''}>
                                Pause
                            </button>
                            <button class="btn btn-resume" onclick="dashboard.executeAction('${agent.id}', 'resume')" ${!canResume ? 'disabled' : ''}>
                                Resume
                            </button>
                            <button class="btn btn-stop" onclick="dashboard.executeAction('${agent.id}', 'stop')" ${!canStop ? 'disabled' : ''}>
                                Stop
                            </button>
                            <button class="btn btn-restart" onclick="dashboard.executeAction('${agent.id}', 'restart')">
                                Restart
                            </button>
                            <button class="btn btn-prioritize" onclick="dashboard.executeAction('${agent.id}', 'prioritize', {priority: 'high'})">
                                Prioritize
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = rows;
        
        // Remove animation class after animation completes
        setTimeout(() => {
            document.querySelectorAll('.updating').forEach(el => {
                el.classList.remove('updating');
            });
        }, 1000);
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
        
        const logsHtml = this.logs.map(log => `
            <div class="log-entry">
                <span class="log-timestamp">${log.timestamp}</span>
                <span class="log-level-${log.level}">[${log.level.toUpperCase()}]</span>
                <span class="log-message">${log.message}</span>
            </div>
        `).join('');
        
        container.innerHTML = logsHtml;
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
