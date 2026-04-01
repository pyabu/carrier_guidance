/**
 * AI Career Copilot - Frontend Logic
 * Handles the chatbot UI interactions and API communication.
 */

(function() {
    const chatbotToggle = document.getElementById('chatbotToggle');
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotClose = document.getElementById('chatbotClose');
    const chatbotMessages = document.getElementById('chatbotMessages');
    const chatbotInput = document.getElementById('chatbotInput');
    const chatbotSend = document.getElementById('chatbotSend');
    const chatbotClear = document.getElementById('chatbotClear');
    const typingIndicator = document.getElementById('typingIndicator');

    if (!chatbotToggle || !chatbotWindow) return;

    const escapeHtml = (value) => String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    const formatInlineMarkdown = (value) => value
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/(^|[^\*])\*([^\*\n]+)\*([^\*]|$)/g, '$1<em>$2</em>$3')
        .replace(/📈/g, '<span style="font-size: 1.2rem; display: inline-block;">📈</span>')
        .replace(/🔥/g, '<span style="font-size: 1.2rem; display: inline-block;">🔥</span>')
        .replace(/🛠️/g, '<span style="font-size: 1.2rem; display: inline-block;">🛠️</span>')
        .replace(/🗺️/g, '<span style="font-size: 1.2rem; display: inline-block;">🗺️</span>')
        .replace(/💼/g, '<span style="font-size: 1.2rem; display: inline-block;">💼</span>')
        .replace(/🏢/g, '<span style="font-size: 1.2rem; display: inline-block;">🏢</span>')
        .replace(/💰/g, '<span style="font-size: 1.2rem; display: inline-block;">💰</span>')
        .replace(/📊/g, '<span style="font-size: 1.2rem; display: inline-block;">📊</span>');

    const formatMessage = (text) => {
        const placeholders = [];
        let safeText = escapeHtml(text).replace(/```([\s\S]*?)```/g, (_, code) => {
            const placeholder = `__CHATBOT_CODE_BLOCK_${placeholders.length}__`;
            placeholders.push(
                `<pre style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; overflow-x: auto; margin: 10px 0; font-family: monospace; font-size: 0.8rem;"><code>${code.trim()}</code></pre>`
            );
            return placeholder;
        });

        // Handle job listings/cards
        const jobCardRegex = /\*\*([^*]+)\*\*\s*\n\s*💼\s*([^\n]+)\n\s*💰\s*([^\n]+)/g;
        safeText = safeText.replace(jobCardRegex, (match, title, role, salary) => {
            const jobPlaceholder = `__CHATBOT_JOB_CARD_${placeholders.length}__`;
            placeholders.push(
                `<div style="background: rgba(59, 130, 246, 0.1); border-left: 4px solid #60a5fa; padding: 12px 14px; border-radius: 8px; margin: 8px 0; font-weight: 500;">
                    <div style="color: #60a5fa; font-weight: 700; margin-bottom: 4px;">${title}</div>
                    <div style="font-size: 0.85rem; color: rgba(255, 255, 255, 0.8); margin-bottom: 4px;">💼 ${role}</div>
                    <div style="font-size: 0.85rem; color: #10b981; font-weight: 600;">💰 ${salary}</div>
                </div>`
            );
            return jobPlaceholder;
        });

        const formattedLines = safeText.split('\n').map((line) => {
            const bulletMatch = line.match(/^\s*[\*\-•]\s+(.*)$/);
            if (bulletMatch) {
                const content = bulletMatch[1];
                // Check if it's a salary line with LPA
                if (content.includes('LPA') || content.includes('₹')) {
                    return `<div style="display:flex; gap:8px; margin-bottom:4px; padding-left: 10px; color: #10b981;">
                        <span style="color: #10b981; font-weight: 700;">•</span>
                        <span>${formatInlineMarkdown(content)}</span>
                    </div>`;
                }
                return `<div style="display:flex; gap:8px; margin-bottom:4px; padding-left: 10px;"><span style="color: #60a5fa;">•</span><span>${formatInlineMarkdown(content)}</span></div>`;
            }
            if (!line.trim()) {
                return '<br>';
            }
            return formatInlineMarkdown(line);
        });

        let formattedText = formattedLines.join('<br>');
        placeholders.forEach((block, index) => {
            formattedText = formattedText.replace(`__CHATBOT_CODE_BLOCK_${index}__`, block);
            formattedText = formattedText.replace(`__CHATBOT_JOB_CARD_${index}__`, block);
        });
        return formattedText;
    };

    // Clear Chat Functionality
    if (chatbotClear) {
        chatbotClear.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (confirm('Clear your conversation history?')) {
                try {
                    await fetch('/api/career_copilot/clear', { method: 'POST' });
                    if (chatbotMessages) {
                        // Restore the original welcome state after clearing the session.
                        const firstMsg = chatbotMessages.querySelector('[data-chatbot-welcome="true"]');
                        chatbotMessages.innerHTML = '';
                        if (firstMsg) chatbotMessages.appendChild(firstMsg);
                        if (typingIndicator) chatbotMessages.appendChild(typingIndicator);
                    }
                } catch (err) {
                    console.error('Failed to clear chat:', err);
                }
            }
        });
    }

    // Toggle Chat Window
    chatbotToggle.addEventListener('click', (e) => {
        e.preventDefault();
        chatbotWindow.classList.toggle('active');
        if (chatbotWindow.classList.contains('active')) {
            setTimeout(() => chatbotInput && chatbotInput.focus(), 100);
        }
    });

    if (chatbotClose) {
        chatbotClose.addEventListener('click', (e) => {
            e.preventDefault();
            chatbotWindow.classList.remove('active');
        });
    }

    // Scroll to bottom helper
    const scrollToBottom = () => {
        if (chatbotMessages) {
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        }
    };

    // Send Message Function
    const sendMessage = async () => {
        if (!chatbotInput) return;
        const message = chatbotInput.value.trim();
        if (!message) return;

        // Disable input while processing
        chatbotInput.disabled = true;
        if (chatbotSend) chatbotSend.disabled = true;

        // Add user message to UI
        addMessage(message, 'user');
        chatbotInput.value = '';

        // Show typing indicator
        if (typingIndicator) {
            typingIndicator.style.display = 'flex';
            scrollToBottom();
        }

        // Timeout controller — 30s for Gemini (it can take time to think)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000);

        try {
            const response = await fetch('/api/career_copilot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            // Handle non-JSON HTML error pages (like Vercel 504 timeouts)
            const contentType = response.headers.get('content-type') || '';

            if (!response.ok) {
                if (contentType.includes('application/json')) {
                    try {
                        const errorJson = await response.json();
                        addMessage(errorJson.error || "Server error occurred. Please try again.", 'ai', true);
                    } catch (e) {
                        addMessage("Server error occurred. Please try again.", 'ai', true);
                    }
                } else {
                    addMessage("Server took too long or returned an error. Please try again.", 'ai', true);
                }
                return;
            }

            if (!contentType.includes('application/json')) {
                addMessage("Received an unexpected response from the server. Please try again.", 'ai', true);
                return;
            }

            const data = await response.json();

            if (data.status === 'success' && data.response) {
                addMessage(data.response, 'ai');
                // Add quick suggestions after AI response
                addQuickSuggestions();
            } else {
                addMessage(data.error || "I'm sorry, I encountered an error. Please try again.", 'ai', true);
            }
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                addMessage("Request timed out. The AI took too long to respond. Please try again.", 'ai', true);
            } else {
                addMessage("Connection error. Please check your internet and try again.", 'ai', true);
            }
            console.error('Chatbot Error:', error);
        } finally {
            // Hide typing indicator safely
            if (typingIndicator) {
                typingIndicator.style.display = 'none';
            }
            // Re-enable input
            if (chatbotInput) {
                chatbotInput.disabled = false;
                chatbotInput.focus();
            }
            if (chatbotSend) chatbotSend.disabled = false;
        }
    };

    // Add Quick Suggestion Buttons
    const addQuickSuggestions = () => {
        if (!chatbotMessages) return;
        
        const suggestions = [
            "Tell me more details",
            "Job opportunities",
            "Required skills",
            "Learning roadmap"
        ];

        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.style.cssText = 'display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; padding: 0 20px; animation: message-in 0.35s cubic-bezier(0.16, 1, 0.3, 1) forwards, opacity 0;';
        suggestionsDiv.className = 'chatbot-suggestions';
        
        suggestions.forEach((suggestion) => {
            const btn = document.createElement('button');
            btn.textContent = suggestion;
            btn.style.cssText = 'padding: 6px 12px; background: rgba(59, 130, 246, 0.2); border: 1px solid rgba(96, 165, 250, 0.4); border-radius: 16px; color: #60a5fa; font-size: 0.8rem; cursor: pointer; transition: all 0.2s; white-space: nowrap;';
            btn.addEventListener('mouseover', () => {
                btn.style.background = 'rgba(59, 130, 246, 0.3)';
                btn.style.borderColor = '#60a5fa';
            });
            btn.addEventListener('mouseout', () => {
                btn.style.background = 'rgba(59, 130, 246, 0.2)';
                btn.style.borderColor = 'rgba(96, 165, 250, 0.4)';
            });
            btn.addEventListener('click', () => {
                chatbotInput.value = suggestion;
                chatbotInput.focus();
                sendMessage();
                [...suggestionsDiv.children].forEach(b => b.remove());
            });
            suggestionsDiv.appendChild(btn);
        });
        
        chatbotMessages.appendChild(suggestionsDiv);
        scrollToBottom();
    };

    // Add Message to UI
    const addMessage = (text, sender, isError) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');

        // Add sender class(es) — handle 'ai', 'user'
        messageDiv.classList.add(sender);

        // Add error styling if flagged
        if (isError) {
            messageDiv.classList.add('error-msg');
        }
        
        const formattedText = formatMessage(text);
        messageDiv.innerHTML = formattedText;

        // Insert before typing indicator (so it appears above it)
        if (typingIndicator && typingIndicator.parentNode === chatbotMessages) {
            chatbotMessages.insertBefore(messageDiv, typingIndicator);
        } else {
            chatbotMessages.appendChild(messageDiv);
        }
        
        // Scroll to bottom (with small delay for rendering)
        setTimeout(scrollToBottom, 50);
    };

    // Event Listeners for sending
    if (chatbotSend) {
        chatbotSend.addEventListener('click', sendMessage);
    }
    if (chatbotInput) {
        chatbotInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
})();
