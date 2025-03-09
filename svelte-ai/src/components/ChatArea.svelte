<script>
    import { marked } from "marked";
    import ChatSidebar from "./ChatSidebar.svelte";

    export let chatHistory = [];
    export let currentResponse = "";
    export let loading = false;
    export let message = "";
    export let chatId = "";
    export let fileInput;

    let availableChats = [];

    function parseMarkdown(text) {
        return marked.parse(text, { breaks: true, gfm: true });
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (!message.trim()) return;

        const chatId = initializeChatId();
        chatHistory = [...chatHistory, { role: "user", content: message }];
        loading = true;
        currentResponse = "";

        try {
            const res = await fetch("http://localhost:5001/chat", {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: new URLSearchParams({ message, chat_id: chatId }),
            });

            if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);

            const reader = res.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n\n");

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const data = line.replace("data: ", "").trim();
                        if (data === "[DONE]") {
                            chatHistory = [...chatHistory, { role: "ai", content: currentResponse }];
                            currentResponse = "";
                            loading = false;
                            await loadChatHistory();
                        } else {
                            currentResponse += data + "\n";
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Fetch streaming error:", error);
            currentResponse = `Error: ${error.message}`;
            chatHistory = [...chatHistory, { role: "ai", content: currentResponse }];
            loading = false;
            await loadChatHistory();
        }

        message = "";
    }

    async function handleImageSubmit(event) {
        event.preventDefault();
        if (!fileInput.files || fileInput.files.length === 0) return;

        const file = fileInput.files[0];
        const imageUrl = URL.createObjectURL(file);
        const chatId = initializeChatId();
        const formData = new FormData();
        formData.append("file", file);
        formData.append("chat_id", chatId);

        chatHistory = [...chatHistory, { role: "user", content: `Uploaded image: ${file.name}`, image: imageUrl }];
        loading = true;
        currentResponse = "";

        try {
            const res = await fetch("http://localhost:5001/image", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);

            const reader = res.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n\n");

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const data = line.replace("data: ", "").trim();
                        if (data === "[DONE]") {
                            chatHistory = [...chatHistory, { role: "ai", content: currentResponse }];
                            currentResponse = "";
                            loading = false;
                            await loadChatHistory();
                        } else {
                            currentResponse += data + "\n";
                        }
                    }
                }
            }
        } catch (error) {
            console.error("Image streaming error:", error);
            currentResponse = `Error: ${error.message}`;
            chatHistory = [...chatHistory, { role: "ai", content: currentResponse }];
            loading = false;
            await loadChatHistory();
        }

        fileInput.value = "";
    }

    function handleSelectChat(selectedChatId) {
        if (selectedChatId) {
            loadChat(selectedChatId);
        } else {
            chatId = "";
            chatHistory = [];
            currentResponse = "";
        }
    }

    async function loadChat(selectedChatId) {
        try {
            const res = await fetch(`http://localhost:5001/history?chat_id=${selectedChatId}`);
            const data = await res.json();
            if (data.messages) {
                chatHistory = data.messages.map((msg) => ({
                    role: msg.role,
                    content: msg.content,
                    image: msg.role === "user" && msg.content.startsWith("Uploaded image:") ? null : undefined,
                }));
                chatId = selectedChatId;
            }
        } catch (error) {
            console.error("Error loading chat:", error);
        }
    }

    function initializeChatId() {
        if (!chatId) {
            chatId = crypto.randomUUID();
        }
        return chatId;
    }

    async function startNewChat() {
        chatHistory = [];
        chatId = crypto.randomUUID();
        currentResponse = "";
        message = "";
        await loadChatHistory();
    }

    async function loadChatHistory() {
        try {
            const res = await fetch("http://localhost:5001/history");
            const data = await res.json();
            availableChats = data.chats || [];
        } catch (error) {
            console.error("Error loading chat history:", error);
        }
    }
</script>

<div class="chat-area">
    <ChatSidebar 
        {availableChats} 
        onSelectChat={handleSelectChat} 
        {loading}
    />
    <div class="chat-content">
        <nav class="chat-navbar">
            <button 
                class="nav-btn" 
                on:click={startNewChat}
                disabled={loading}
            >
                New Chat
            </button>
        </nav>
        <div class="chat-container">
            {#each chatHistory as { role, content, image }, i}
                <div class="message {role}">
                    <strong>{role === "user" ? "You" : "AI"}:</strong>
                    {#if role === "ai"}
                        <span class="content">{@html parseMarkdown(content)}</span>
                    {:else}
                        <span class="content">{content}</span>
                        {#if image}
                            <img src={image} alt={content.replace("Uploaded image:", "User-uploaded content:")} class="preview" />
                        {/if}
                    {/if}
                </div>
            {/each}
            {#if currentResponse}
                <div class="message ai">
                    <strong>AI:</strong>
                    <span class="content">{@html parseMarkdown(currentResponse)}</span>
                </div>
            {/if}
            {#if loading && !currentResponse}
                <div class="message ai">
                    <strong>AI:</strong>
                    <span class="content">Processing...</span>
                </div>
            {/if}
            {#if !chatId && chatHistory.length === 0}
                <p>Type a message or upload an image to begin.</p>
            {/if}
        </div>
        <form on:submit={handleSubmit}>
            <input
                type="text"
                bind:value={message}
                placeholder="Type a message"
                disabled={loading}
            />
            <label for="image-upload" class="image-button" title="Upload an image">
                📷
            </label>
            <input
                type="file"
                id="image-upload"
                accept="image/png, image/jpeg, image/gif"
                bind:this={fileInput}
                on:change={handleImageSubmit}
                disabled={loading}
                hidden
            />
            <button type="submit" disabled={loading}>
                {loading ? "Sending..." : "Send"}
            </button>
        </form>
    </div>
</div>

<style>
    .chat-area {
        display: flex;
        height: 100%; /* Inherits from parent (App.svelte) */
        overflow: hidden; /* Prevent scrolling at this level */
    }

    .chat-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        width: calc(100% - 300px); /* Adjust based on sidebar width */
        height: 100%; /* Ensure it takes full height */
        overflow: hidden; /* Prevent scrolling here too */
    }

    .chat-navbar {
        display: flex;
        gap: 0.5em;
        padding: 0.5em;
        background-color: #f5f5f5;
        border-bottom: 1px solid #ccc;
        flex-shrink: 0; /* Prevent navbar from shrinking */
    }

    .nav-btn {
        padding: 0.5em 1em;
        background-color: #ff3e00;
        color: white;
        border: none;
        border-radius: 3px;
        cursor: pointer;
    }

    .nav-btn:disabled {
        background-color: #a56161;
        cursor: not-allowed;
    }

    .nav-btn:hover:not(:disabled) {
        background-color: #e63900;
    }

    .chat-container {
        flex: 1; /* Take remaining space */
        overflow-y: auto; /* Allow scrolling within messages only */
        border: 1px solid #ccc;
        padding: 1em;
        background-color: #f9f9f9;
        scroll-behavior: smooth;
    }

    .message {
        margin: 0.5em 0;
        padding: 0.5em;
        border-radius: 5px;
    }

    .user {
        background-color: #e0f7fa;
        text-align: right;
    }

    .ai {
        background-color: #f1f8e9;
        text-align: left;
    }

    .content {
        display: block;
        word-wrap: break-word;
    }

    .preview {
        max-width: 200px;
        max-height: 200px;
        margin-top: 0.5em;
        border-radius: 5px;
        display: block;
    }

    form {
        display: flex;
        gap: 0.5em;
        padding: 0.5em;
        background-color: #fff;
        align-items: center;
        flex-shrink: 0; /* Prevent form from shrinking */
        border-top: 1px solid #ccc;
    }

    input[type="text"] {
        flex: 1;
        padding: 0.5em;
        border: 1px solid #ccc;
        border-radius: 3px;
    }

    .image-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2em;
        height: 2em;
        font-size: 1.2em;
        cursor: pointer;
        border: 1px solid #ccc;
        border-radius: 3px;
        background-color: rgb(255, 255, 255);
    }

    .image-button:hover:not(:disabled) {
        background-color: rgb(127, 129, 147);
    }

    input[type="file"] {
        display: none;
    }

    button {
        padding: 0.5em 1em;
        background-color: #ff3e00;
        color: white;
        border: none;
        border-radius: 3px;
        cursor: pointer;
    }

    button:disabled {
        background-color: #a56161;
        cursor: not-allowed;
    }
</style>