/**
 * AI Career Copilot - Frontend Logic
 * Handles the chatbot UI interactions and API communication.
 */

document.addEventListener('DOMContentLoaded', () => {
    const chatbotToggle = document.getElementById('chatbotToggle');
    const chatbotWindow = document.getElementById('chatbotWindow');
    const chatbotClose = document.getElementById('chatbotClose');
    const chatbotMessages = document.getElementById('chatbotMessages');
    const chatbotInput = document.getElementById('chatbotInput');
    const chatbotSend = document.getElementById('chatbotSend');
    const typingIndicator = document.getElementById('typingIndicator');

    // Toggle Chat Window
    chatbotToggle.addEventListener('click', () => {
        chatbotWindow.classList.add('active');
        chatbotInput.focus();
    });

    chatbotClose.addEventListener('click', () => {
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
        typingIndicator.style.display = 'block';
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

        try {
            const response = await fetch('/api/career_copilot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message }),
            });

            const data = await response.json();
            
            // Hide typing indicator
            typingIndicator.style.display = 'none';

            if (data.status === 'success') {
                addMessage(data.response, 'ai');
            } else {
                addMessage(data.error || "I'm sorry, I encountered an error. Please try again.", 'ai');
            }
        } catch (error) {
            typingIndicator.style.display = 'none';
            addMessage("Connection error. Please check your internet and try again.", 'ai');
            console.error('Chatbot Error:', error);
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
    chatbotSend.addEventListener('click', sendMessage);
    chatbotInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});
