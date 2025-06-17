document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatWindow = document.getElementById('chat-window');
    const debugToggle = document.getElementById('debug-toggle');
    const debugPanel = document.getElementById('debug-panel');
    const debugContent = document.getElementById('debug-content');
    const attachFileBtn = document.getElementById('attach-file-btn');
    const imageInput = document.getElementById('image-input');
    const imagePreviewContainer = document.getElementById('image-preview-container');
    const imagePreview = document.getElementById('image-preview');
    const removeImageBtn = document.getElementById('remove-image-btn');

    let imageBase64 = null;

    // --- Event Listeners ---
    debugToggle.addEventListener('change', () => {
        debugPanel.classList.toggle('hidden', !debugToggle.checked);
    });

    attachFileBtn.addEventListener('click', () => imageInput.click());

    imageInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                imageBase64 = e.target.result;
                imagePreview.src = imageBase64;
                imagePreviewContainer.classList.remove('hidden');
            };
            reader.readAsDataURL(file);
        }
    });

    removeImageBtn.addEventListener('click', () => {
        imageBase64 = null;
        imageInput.value = ''; // Reset the file input
        imagePreviewContainer.classList.add('hidden');
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const userInput = messageInput.value.trim();
        if (!userInput && !imageBase64) return;

        displayMessage(userInput, 'user');
        messageInput.value = '';

        const payload = buildPayload(userInput, imageBase64);

        // Clear preview after sending
        removeImageBtn.click(); 

        try {
            const response = await fetch('/v1/chat/completions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();
            const aiResponse = data.choices[0].message.content;
            displayMessage(aiResponse, 'assistant');

            // Update debugger
            debugContent.textContent = JSON.stringify(data.debug_info, null, 2);

        } catch (error) {
            console.error('Fetch error:', error);
            displayMessage(`Error: Could not connect to the agent. ${error.message}`, 'error');
        }
    });

    // --- Helper Functions ---
    function buildPayload(text, image) {
        const content = [];
        if (text) {
            content.push({ type: 'text', text: text });
        }
        if (image) {
            content.push({ 
                type: 'image_url', 
                image_url: { url: image }
            });
        }
        return { messages: [{ role: 'user', content: content }] };
    }

    function displayMessage(text, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        // A simple markdown-to-html for code blocks and bold
        let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        formattedText = formattedText.replace(/```(\w+)?\n([\s\S]+?)```/g, '<pre><code>$2</code></pre>');
        messageDiv.innerHTML = formattedText;
        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    // Initial welcome message
    displayMessage("Welcome to StateAgent v0.2. How can I assist you?", "assistant");
});