(function() {
    // Load Marked.js if not already loaded
    function loadMarked(callback) {
        if (window.marked) {
            callback();
            return;
        }

        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js';
        script.onload = callback;
        script.onerror = () => {
            console.error('Failed to load Marked.js');
            callback(); // Continue without markdown support
        };
        document.head.appendChild(script);
    }

    // Initialize widget after Marked.js is loaded
    loadMarked(() => {
        const config = {
            chatbotName: '{{ chatbot_name|escapejs }}',
            chatbotLogo: '{{ chatbot_logo|escapejs }}',
            baseUrl: '{{ base_url|escapejs }}'
        };

        // Inject CSS styles
        const styles = `
            /* Isolate chatbot from external styles */
            #mv-chatbot-widget-root,
            #mv-chatbot-widget-root * {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
                line-height: 20px;
                box-sizing: border-box !important;
            }

            /* Override any Bootstrap classes that might affect our elements */
            #mv-chatbot-widget-root .btn,
            #mv-chatbot-widget-root .form-control,
            #mv-chatbot-widget-root .container,
            #mv-chatbot-widget-root .row,
            #mv-chatbot-widget-root .col {
                all: unset !important;
                width: auto !important;
                height: auto !important;
                margin: 0 !important;
                padding: 0 !important;
                border: none !important;
                background: none !important;
            }

            #mv-chatbot-widget-root {
                z-index: 99999;
            }

            #mv-chatbot-fab {
                position: fixed;
                right: 32px;
                bottom: 32px;
                background: #290a4e;
                border-radius: 50%;
                width: 56px;
                height: 56px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.18);
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: box-shadow 0.2s;
                z-index: 99999;
            }

            #mv-chatbot-fab:hover {
                box-shadow: 0 8px 24px rgba(0,123,255,0.18);
                background: rgb(59, 13, 116);
            }

            #mv-chatbot-modal {
                position: fixed;
                right: 10px;
                bottom: 100px;
                width: 370px;
                max-width: 95vw;
                height: 620px;
                background: #fff;
                border-radius: 10px;
                box-shadow: 0 8px 32px rgba(0,0,0,0.18);
                display: flex;
                flex-direction: column;
                z-index: 99999;
                overflow: hidden;
                animation: mv-chatbot-fadein 0.2s;
                border: 1px solid rgb(196, 196, 196);
            }
            p{
                margin-bottom: 0px;
            }

            @keyframes mv-chatbot-fadein {
                from { opacity: 0; transform: translateY(40px); }
                to { opacity: 1; transform: translateY(0); }
            }

            #mv-chatbot-header {
                background: #eaeaea;
                color: #1c1c1c;
                padding: 12px 18px 12px 14px;
                font-size: 1.2rem;
                font-weight: 600;
                display: flex;
                align-items: center;
                justify-content: space-between;
                border-bottom: 1px solid #e0e0e0;
                min-height: 60px;
            }

            .header-left {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .logo-icon {
                width: 38px;
                height: 38px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #fff;
                border-radius: 50%;
                box-shadow: 0 2px 8px rgba(0,123,255,0.07);
            }

            .header-title {
                display: flex;
                flex-direction: column;
                justify-content: center;
            }

            .main-title {
                font-size: 1.08rem;
                font-weight: 700;
                color: #222;
                margin-bottom: 2px;
                letter-spacing: 0.2px;
            }

            .sub-title {
                font-size: 0.93rem;
                color: #555;
                font-weight: 300;
                letter-spacing: 0.1px;
            }

            #mv-chatbot-close {
                background: none;
                border: none;
                padding: 4px;
                margin-left: 8px;
                cursor: pointer;
                border-radius: 50%;
                transition: background 0.18s;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            #mv-chatbot-close:hover {
                background: #e0eaff;
            }

            #mv-chatbot-messages {
                flex: 1;
                overflow-y: auto;
                padding: 18px 10px 10px 10px;
                background: #f4f4f4;
                display: flex;
                flex-direction: column;
                scrollbar-width: thin;
                scrollbar-color: #cecece #e0e0e000;
            }

            #mv-chatbot-messages::-webkit-scrollbar {
                width: 8px;
                border-radius: 8px;
                background: #e0e0e0;
            }

            #mv-chatbot-messages::-webkit-scrollbar-thumb {
                background: linear-gradient(135deg, #007bff 40%, #0056b3 100%);
                border-radius: 8px;
            }

            .mv-chatbot-message {
                margin-bottom: 15px;
                max-width: 75%;
                padding: 12px 16px;
                border-radius: 16px;
                word-wrap: break-word;
                font-size: 1rem;
                padding-bottom: 0px;
            }

            .mv-chatbot-message p {
                margin: 0px;
            }

            .mv-chatbot-user-msg {
                background-color: #1c1c1c;
                color: white;
                align-self: flex-end;
                border-bottom-right-radius: 0;
                text-align: right;
            }

            .mv-chatbot-bot-msg {
                background-color: #cbcbcb;
                align-self: flex-start;
                border-bottom-left-radius: 0;
            }

            #mv-chatbot-input-bar {
                display: flex;
                background-color: white;
                border-top: 1px solid #d3d3d3;
                flex-direction: row;
                border-radius: 0 0 18px 18px;
                align-items: center;
                padding: 10px;
                gap: 8px;
            }

            #mv-chatbot-user-input {
                flex: 1;
                padding: 12px 14px;
                border-radius: 10px;
                border: none;
                font-size: 1rem;
                min-height: 44px;
                max-height: 120px;
                resize: vertical;
                background: #ffffff00;
                transition: border-color 0.2s, box-shadow 0.2s;
                outline: none;
                font-family: Arial, Helvetica, sans-serif;
            }

            #mv-chatbot-send-btn {
                background-color: #2a2a2a;
                color: white;
                padding: 10px 14px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 1rem;
                font-weight: 500;
                transition: background 0.2s;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            #mv-chatbot-send-btn:hover {
                background-color: #0056b3;
            }

            .mv-typing-indicator {
                display: flex;
                align-items: center;
                gap: 2px;
                font-style: italic;
                font-size: 0.98em;
                color: #393939;
                padding: 8px 12px;
                background: rgb(255, 255, 255);
                border-radius: 12px;
                margin: 8px 0;
                width: fit-content;
            }

            .mv-typing-indicator .dot {
                height: 8px;
                width: 8px;
                margin: 0 2px;
                background-color: rgb(103, 103, 103);
                border-radius: 50%;
                display: inline-block;
                animation: bounce 1.2s infinite both;
            }

            .mv-typing-indicator .dot:nth-child(1) { animation-delay: 0s; }
            .mv-typing-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
            .mv-typing-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

            @keyframes bounce {
                0%, 80%, 100% { transform: translateY(0); }
                40% { transform: translateY(-8px); }
            }

            .devlop-credit {
                font-size: 10px;
                text-align: center;
                padding-bottom: 2px;
            }

            .message {
                margin-bottom: 15px;
                max-width: 75%;
                display: flex;
                flex-direction: column;
            }

            .message-left {
                align-self: flex-start;
            }

            .message-right {
                align-self: flex-end;
            }

            .message-content {
                padding: 12px 16px;
                border-radius: 16px;
                word-wrap: break-word;
                white-space: pre-wrap;
                font-size: 1rem;
                line-height: 1.4;
            }

            .message-left .message-content {
                background-color: #cbcbcb;
                color: #1c1c1c;
                border-bottom-left-radius: 4px;
            }

            .message-right .message-content {
                background-color: #1c1c1c;
                color: white;
                border-bottom-right-radius: 4px;
                text-align: right;
            }

            .message-time {
                font-size: 0.75rem;
                margin-top: 4px;
                opacity: 0.7;
            }

            .message-left .message-time {
                color: #666;
                margin-left: 4px;
            }

            .message-right .message-time {
                color: #666;
                margin-right: 4px;
                text-align: right;
            }

            .mv-widget-header-container {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .mv-widget-logo-wrapper {
                width: 38px;
                height: 38px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #fff;
                border-radius: 50%;
                box-shadow: 0 2px 8px rgba(0,123,255,0.07);
            }

            .mv-widget-title-container {
                display: flex;
                flex-direction: column;
                justify-content: center;
            }

            .mv-widget-chatbot-name {
                font-size: 1.08rem;
                font-weight: 700;
                color: #222222;
                margin-bottom: 2px;
                letter-spacing: 0.2px;
            }

            .mv-widget-chatbot-subtitle {
                font-size: 0.93rem;
                color: #555555;
                font-weight: 300;
                letter-spacing: 0.1px;
            }

            .mv-widget-chat-bubble {
                margin-bottom: 15px;
                max-width: 75%;
                padding: 12px 16px;
                border-radius: 16px;
                word-wrap: break-word;
                font-size: 1rem;
            }
            .mv-widget-chat-bubble p{
                font-size: 1rem;
                font-weight: 400;
            }

            .mv-widget-user-bubble {
                background-color: #1c1c1c;
                color: #ffffff;
                align-self: flex-end;
                border-bottom-right-radius: 0;
                text-align: right;
            }

            .mv-widget-user-bubble p {
                color: #ffffff;
            }

            .mv-widget-bot-bubble {
                background-color: #cbcbcb;
                color: #1c1c1c;
                align-self: flex-start;
                border-bottom-left-radius: 0;
            }
            .mv-widget-bot-bubble p {
                color: #1c1c1c;
            }

            .mv-widget-timestamp {
                font-size: 0.75rem;
                margin-top: 4px;
                opacity: 0.7;
                color: #666666;
            }
        `;

        // Create and inject style element
        const styleEl = document.createElement('style');
        styleEl.textContent = styles;
        document.head.appendChild(styleEl);

        // Create widget HTML structure
        const widgetHtml = `
            <div id="mv-chatbot-widget-root">
                <div id="mv-chatbot-fab" onclick="querySafe.toggleWidget()">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="#fff">
                        <circle cx="12" cy="12" r="12" fill="#4b1a86"/>
                        <path d="M7 17v-2a4 4 0 0 1 4-4h2a4 4 0 0 1 4 4v2" stroke="#fff" stroke-width="2" fill="none"/>
                        <circle cx="9" cy="10" r="1" fill="#fff"/>
                        <circle cx="15" cy="10" r="1" fill="#fff"/>
                    </svg>
                </div>
                <div id="mv-chatbot-modal">
                    <div id="mv-chatbot-header">
                        <div class="mv-widget-header-container">
                            <div class="mv-widget-logo-wrapper">
                                ${config.chatbotLogo ? 
                                    `<img src="${config.chatbotLogo}" alt="${config.chatbotName}" width="32" height="32">` :
                                    `<svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                                        <circle cx="16" cy="16" r="16" fill="#4b1a86"/>
                                        <text x="16" y="21" text-anchor="middle" font-size="16" fill="#fff" font-family="system-ui">${config.chatbotName.slice(0,2)}</text>
                                    </svg>`
                                }
                            </div>
                            <div class="mv-widget-title-container">
                                <div class="mv-widget-chatbot-name">${config.chatbotName}</div>
                                <div class="mv-widget-chatbot-subtitle">AI Assistant</div>
                            </div>
                        </div>
                        <button id="mv-chatbot-close" onclick="querySafe.toggleWidget()" title="Close">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                                <circle cx="12" cy="12" r="12" fill="#f4f4f4"/>
                                <path d="M8 8l8 8M16 8l-8 8" stroke="#191919" stroke-width="2" stroke-linecap="round"/>
                            </svg>
                        </button>
                    </div>
                    <div id="mv-chatbot-messages"></div>
                    <div id="mv-chatbot-input-bar">
                        <textarea id="mv-chatbot-user-input" placeholder="Type your message..." rows="2"></textarea>
                        <button id="mv-chatbot-send-btn" onclick="querySafe.sendMessage()" title="Send">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="#fff">
                                <path d="M2 21l21-9-21-9v7l15 2-15 2z" fill="#fff"/>
                            </svg>
                        </button>
                    </div>
                    <div class="devlop-credit">Made with ❤ by Metric Vibes</div>
                </div>
            </div>
        `;

        // Create global namespace for widget
        window.querySafe = {
            config: config,
            chatHistory: [],
            isOpen: false,
            conversationId: null,
            greetingSent: false,

            init: function() {
                const container = document.createElement('div');
                container.innerHTML = widgetHtml;
                document.body.appendChild(container);
                this.bindEvents();
                
                // Initialize modal state
                const modal = document.getElementById('mv-chatbot-modal');
                modal.style.display = 'none';
            },

            bindEvents: function() {
                const input = document.getElementById('mv-chatbot-user-input');
                const sendBtn = document.getElementById('mv-chatbot-send-btn');

                if (input) {
                    // Handle Enter key
                    input.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            const message = input.value.trim();
                            if (message) {
                                this.sendMessage(message);
                                input.value = '';
                            }
                        }
                    });

                    // Auto resize textarea
                    input.addEventListener('input', () => {
                        input.style.height = 'auto';
                        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
                    });
                }

                if (sendBtn) {
                    sendBtn.addEventListener('click', () => {
                        const message = input.value.trim();
                        if (message) {
                            this.sendMessage(message);
                            input.value = '';
                            input.style.height = 'auto';
                        }
                    });
                }
            },

            toggleWidget: function() {
                const modal = document.getElementById('mv-chatbot-modal');
                this.isOpen = !this.isOpen;
                modal.style.display = this.isOpen ? 'flex' : 'none';
                
                if (this.isOpen && !this.greetingSent) {
                    this.displayMessage('Hi! How can I help you today?', false);
                    this.greetingSent = true;
                }

                if (this.isOpen) {
                    document.getElementById('mv-chatbot-user-input').focus();
                }
            },

            displayMessage: function(message, isUser) {
                const messagesDiv = document.getElementById('mv-chatbot-messages');
                const messageDiv = document.createElement('div');
                messageDiv.className = `mv-widget-chat-bubble ${isUser ? 'mv-widget-user-bubble' : 'mv-widget-bot-bubble'}`;

                // Format message with or without markdown
                if (window.marked) {
                    try {
                        marked.setOptions({
                            breaks: true,
                            gfm: true,
                            headerIds: false,
                            mangle: false,
                            sanitize: false
                        });
                        messageDiv.innerHTML = marked.parse(message);
                    } catch (error) {
                        console.warn('Markdown parsing failed, falling back to plain text');
                        messageDiv.textContent = message;
                    }
                } else {
                    messageDiv.textContent = message;
                }

                // Add timestamp
                const timeDiv = document.createElement('div');
                timeDiv.className = 'mv-widget-timestamp';
                timeDiv.textContent = new Date().toLocaleTimeString([], { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                });
                messageDiv.appendChild(timeDiv);
                
                messagesDiv.appendChild(messageDiv);
                messagesDiv.scrollTo({
                    top: messagesDiv.scrollHeight,
                    behavior: 'smooth'
                });
            },

            sendMessage: function(message) {
                // Display user message immediately
                this.displayMessage(message, true);
                
                // Show loading indicator
                const loadingId = this.showLoadingMessage();
                
                // Send to server
                fetch(`${this.config.baseUrl}/chat/`, {
                    method: 'POST',
                    mode: 'cors', // Enable CORS
                    credentials: 'omit', // Don't send credentials
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        query: message,
                        chatbot_id: '{{ chatbot.chatbot_id }}',
                        conversation_id: this.conversationId
                    })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    // Remove loading message
                    this.removeLoadingMessage(loadingId);
                    
                    if (data.error) {
                        throw new Error(data.error);
                    }
                    if (data.conversation_id) {
                        this.conversationId = data.conversation_id;
                    }
                    if (data.answer) {
                        this.displayMessage(data.answer, false);
                    }
                })
                .catch(error => {
                    // Remove loading message
                    this.removeLoadingMessage(loadingId);
                    
                    console.error('querySafe Error:', error);
                    this.displayMessage('Sorry, something went wrong. Please try again.', false);
                });
            },

            // Add these helper methods for loading indicator
            showLoadingMessage: function() {
                const messagesDiv = document.getElementById('mv-chatbot-messages');
                const loadingDiv = document.createElement('div');
                const id = 'loading-' + Date.now();
                loadingDiv.id = id;
                loadingDiv.className = 'message message-left';
                loadingDiv.innerHTML = `
                    <div class="message-content mv-typing-indicator">
                        <span class="dot"></span>
                        <span class="dot"></span>
                        <span class="dot"></span>
                        <span style="margin-left:8px;">Agent is typing...</span>
                    </div>
                `;
                messagesDiv.appendChild(loadingDiv);
                messagesDiv.scrollTo({
                    top: messagesDiv.scrollHeight,
                    behavior: 'smooth'
                });
                return id;
            },

            removeLoadingMessage: function(id) {
                const loadingDiv = document.getElementById(id);
                if (loadingDiv) {
                    loadingDiv.remove();
                }
            },

            setInputEnabled: function(enabled) {
                const input = document.getElementById('mv-chatbot-user-input');
                const btn = document.getElementById('mv-chatbot-send-btn');
                input.disabled = !enabled;
                btn.disabled = !enabled;
                if (enabled) {
                    input.focus();
                }
            }
        };

        // Initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => querySafe.init());
        } else {
            querySafe.init();
        }
    });
})();