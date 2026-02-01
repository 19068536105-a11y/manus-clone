// DOM 元素
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

// 后端API地址
const API_URL = 'http://localhost:8000';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    messageInput.focus();
    initTextareaAutoResize();
});

// 输入框高度自适应
function initTextareaAutoResize() {
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
        updateSendButtonState();
    });
}

// 更新发送按钮状态
function updateSendButtonState() {
    const hasContent = messageInput.value.trim().length > 0;
    sendBtn.disabled = !hasContent;
}

// 发送消息
async function sendMessage() {
    const content = messageInput.value.trim();
    if (!content) return;
    
    hideWelcomeMessage();
    addMessage(content, 'user');
    
    messageInput.value = '';
    messageInput.style.height = 'auto';
    updateSendButtonState();
    
    // 使用SSE流式接收
    await streamChat(content);
}

// 隐藏欢迎消息
function hideWelcomeMessage() {
    const welcomeMessage = document.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }
}

// 添加消息到聊天区域
function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = type === 'user' ? '我' : 'M';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(messageContent);
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
    
    return messageDiv;
}

// 添加状态消息（规划中、执行中等）
function addStatusMessage(text) {
    const statusDiv = document.createElement('div');
    statusDiv.className = 'message ai status-message';
    statusDiv.id = 'currentStatus';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'M';
    
    const content = document.createElement('div');
    content.className = 'message-content status-content';
    content.innerHTML = `
        <div class="status-indicator">
            <div class="spinner"></div>
            <span>${text}</span>
        </div>
    `;
    
    statusDiv.appendChild(avatar);
    statusDiv.appendChild(content);
    chatMessages.appendChild(statusDiv);
    scrollToBottom();
    
    return statusDiv;
}

// 添加Todo清单
function addTodoList(userIntent, todos) {
    // 移除之前的状态消息
    const oldStatus = document.getElementById('currentStatus');
    if (oldStatus) oldStatus.remove();
    
    const todoDiv = document.createElement('div');
    todoDiv.className = 'message ai todo-message';
    todoDiv.id = 'todoList';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'M';
    
    const content = document.createElement('div');
    content.className = 'message-content todo-content';
    
    let todosHtml = todos.map(todo => `
        <div class="todo-item" id="todo-${todo.id}">
            <div class="todo-checkbox">
                <svg class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            </div>
            <span class="todo-text">${todo.task}</span>
        </div>
    `).join('');
    
    content.innerHTML = `
        <div class="todo-header">
            <span class="todo-title">📋 任务规划</span>
            <span class="todo-intent">${userIntent}</span>
        </div>
        <div class="todo-list">
            ${todosHtml}
        </div>
    `;
    
    todoDiv.appendChild(avatar);
    todoDiv.appendChild(content);
    chatMessages.appendChild(todoDiv);
    scrollToBottom();
    
    return todoDiv;
}

// 更新Todo状态
function updateTodoStatus(id, status) {
    const todoItem = document.getElementById(`todo-${id}`);
    if (!todoItem) return;
    
    // 移除所有状态类
    todoItem.classList.remove('pending', 'running', 'done');
    todoItem.classList.add(status);
    
    if (status === 'running') {
        // 添加运行中的动画
        const checkbox = todoItem.querySelector('.todo-checkbox');
        checkbox.innerHTML = '<div class="mini-spinner"></div>';
    } else if (status === 'done') {
        // 显示勾选
        const checkbox = todoItem.querySelector('.todo-checkbox');
        checkbox.innerHTML = `
            <svg class="check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        `;
    }
    
    scrollToBottom();
}

// 添加AI回复
function addAIReply(content) {
    const replyDiv = document.createElement('div');
    replyDiv.className = 'message ai';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'M';
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;
    
    replyDiv.appendChild(avatar);
    replyDiv.appendChild(messageContent);
    chatMessages.appendChild(replyDiv);
    scrollToBottom();
}

// 流式聊天
async function streamChat(userMessage) {
    try {
        const response = await fetch(`${API_URL}/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: userMessage }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const text = decoder.decode(value);
            const lines = text.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        handleSSEEvent(data);
                    } catch (e) {
                        console.error('JSON解析错误:', e);
                    }
                }
            }
        }
        
    } catch (error) {
        console.error('SSE连接失败:', error);
        // 移除状态消息
        const oldStatus = document.getElementById('currentStatus');
        if (oldStatus) oldStatus.remove();
        addAIReply('抱歉，连接服务器失败。请确保后端服务已启动。');
    }
}

// 处理SSE事件
function handleSSEEvent(data) {
    switch (data.type) {
        case 'status':
            addStatusMessage(data.message);
            break;
            
        case 'todo_list':
            addTodoList(data.user_intent, data.todos);
            break;
            
        case 'todo_update':
            updateTodoStatus(data.id, data.status);
            break;
            
        case 'reply':
            addAIReply(data.content);
            break;
            
        case 'done':
            console.log('处理完成');
            break;
    }
}

// 滚动到底部
function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// 事件监听
sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

updateSendButtonState();
