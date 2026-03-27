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
    const typingIndicator = document.getElementById('typingIndicator');

    if (!chatbotToggle || !chatbotWindow) return;

    // Toggle Chat Window
    chatbotToggle.addEventListener('click', (e) => {
        e.preventDefault();
        chatbotWindow.classList.toggle('active');
        if (chatbotWindow.classList.contains('active')) {
            setTimeout(() => chatbotInput.focus(), 100);
        }
    });

    chatbotClose.addEventListener('click', (e) => {
        e.preventDefault();
        chatbotWindow.classList.remove('active');
    });

    // Send Message Function
    const sendMessage = async () => {
        const message = chatbotInput.value.trim();
        if (!message) return;

        // Add user message to UI
        addMessage(message, 'user');
        chatbotInput.value = '';

        // Show typing indicator
        typingIndicator.style.display = 'flex'; // Use flex for our new dots container inline
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

        // Timeout controller
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 seconds timeout

        try {
            const response = await fetch('/api/career_copilot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            // Handle non-JSON HTML error pages (like Vercel 504 timeouts)
            if (!response.ok) {
                const text = await response.text();
                try {
                    const errorJson = JSON.parse(text);
                    addMessage(errorJson.error || "Server error occurred. Please try again.", 'ai error-msg');
                } catch (e) {
                    addMessage("Server took too long or returned an error. Please try again.", 'ai error-msg');
                }
                return;
            }

            const data = await response.json();

            if (data.status === 'success') {
                addMessage(data.response, 'ai');
            } else {
                addMessage(data.error || "I'm sorry, I encountered an error. Please try again.", 'ai error-msg');
            }
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                addMessage("Request timed out. The AI took too long to respond. Please try again.", 'ai error-msg');
            } else {
                addMessage("Connection error. Please check your internet and try again.", 'ai error-msg');
            }
            console.error('Chatbot Error:', error);
        } finally {
            // Hide typing indicator safely
            typingIndicator.style.display = 'none';
        }
    };

    // Add Message to UI
    const addMessage = (text, sender) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        
        // Simple Markdown-ish parsing for better AI responses
        let formattedText = text
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/📈/g, '<span style="font-size: 1.2rem;">📈</span>')
            .replace(/🔥/g, '<span style="font-size: 1.2rem;">🔥</span>')
            .replace(/🛠️/g, '<span style="font-size: 1.2rem;">🛠️</span>')
            .replace(/🗺️/g, '<span style="font-size: 1.2rem;">🗺️</span>');

        messageDiv.innerHTML = formattedText;
        chatbotMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    };

    // Event Listeners for sending
    if (chatbotSend) {
        chatbotSend.addEventListener('click', sendMessage);
    }
    if (chatbotInput) {
        chatbotInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
})();
