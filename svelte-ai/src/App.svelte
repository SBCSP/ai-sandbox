<script>
    import { onMount } from "svelte";
    import Profile from "./components/Profile.svelte";
    import Settings from "./components/Settings.svelte";
    import AppConfig from "./components/AppConfig.svelte";
    import ChatArea from "./components/ChatArea.svelte";

    let message = "";
    let currentResponse = "";
    let chatHistory = [];
    let loading = false;
    let chatContainer;
    let fileInput;
    let chatId = localStorage.getItem("chatId") || "";
    let availableChats = [];
    let selectedOption = '';

    function handleProfileClick() {
        selectedOption = selectedOption === 'Profile' ? '' : 'Profile';
        chatId = '';
        chatHistory = [];
        currentResponse = '';
    }

    function handleSelectOption(option) {
        selectedOption = option;
        chatId = '';
        chatHistory = [];
        currentResponse = '';
    }

    function handleSettingsClick() {
        selectedOption = selectedOption === 'Settings' ? '' : 'Settings';
        chatId = '';
        chatHistory = [];
        currentResponse = '';
    }

    function handleChatClick() {
        selectedOption = selectedOption === 'Chat' ? '' : 'Chat';
    }

    // Generate or reuse chat_id, store in localStorage
    function initializeChatId() {
        if (!chatId) {
            chatId = crypto.randomUUID();
            localStorage.setItem("chatId", chatId);
        }
        return chatId;
    }

    // Load available chats from backend
    async function loadChatHistory() {
        try {
            const res = await fetch("http://localhost:5001/history");
            const data = await res.json();
            availableChats = data.chats || [];
            console.log("Updated availableChats:", availableChats);
        } catch (error) {
            console.error("Error loading chat history:", error);
        }
    }

    // Load a specific chat by chat_id
    async function loadChat(chatId) {
        try {
            const res = await fetch(
                `http://localhost:5001/history?chat_id=${chatId}`,
            );
            const data = await res.json();
            if (data.messages) {
                chatHistory = data.messages.map((msg) => ({
                    role: msg.role,
                    content: msg.content,
                    image:
                        msg.role === "user" &&
                        msg.content.startsWith("Uploaded image:")
                            ? null
                            : undefined,
                }));
                localStorage.setItem("chatId", chatId);
                this.chatId = chatId;
                selectedOption = 'Chat'; // Show chat when loading
            }
            await loadChatHistory();
        } catch (error) {
            console.error("Error loading chat:", error);
        }
    }

    // Clear current chat
    async function clearChat() {
        if (!chatId) return;
        try {
            const res = await fetch(`http://localhost:5001/history/${chatId}`, {
                method: "DELETE",
            });
            const data = await res.json();
            if (res.ok) {
                chatHistory = [];
                localStorage.removeItem("chatId");
                chatId = "";
                await loadChatHistory();
            }
        } catch (error) {
            console.error("Error clearing chat:", error);
        }
    }

    // Start a new chat
    async function startNewChat() {
        chatHistory = [];
        localStorage.removeItem("chatId");
        chatId = crypto.randomUUID();
        localStorage.setItem("chatId", chatId);
        selectedOption = 'Chat'; // Show chat when starting new
        await loadChatHistory();
    }

    // Load chats on mount
    onMount(async () => {
        await loadChatHistory();
        if (chatId) {
            await loadChat(chatId);
        }
    });
</script>

<main>
    <nav class="navbar">
        <div class="navbar-left">
            <img src="/img/main-logo.jpg" alt="AI Sandbox" class="logo" />
        </div>
        <div class="navbar-right">
            <button 
                class="nav-btn" 
                on:click={handleChatClick}
                class:active={selectedOption === 'Chat'}
            >
                💬 Chat
            </button>
            <button 
                class="nav-btn" 
                on:click={handleSettingsClick}
                class:active={selectedOption === 'Settings'}
            >
                ⚙️ Settings
            </button>
            <button 
                class="profile-btn" 
                on:click={handleProfileClick}
                class:active={selectedOption === 'Profile'}
            >
                👤
            </button>
        </div>
    </nav>

    <div class="content-area">
        {#if selectedOption === 'Profile'}
            <Profile />
        {:else if selectedOption === 'Settings'}
            <Settings />
        {:else if selectedOption === 'AppConfig'}
            <AppConfig />
        {:else if selectedOption === 'Chat'}
            <ChatArea 
                bind:chatHistory
                bind:currentResponse
                bind:loading
                bind:message
                bind:chatId
                bind:fileInput
            />
        {/if}
    </div>
</main>

<style>
    main {
        height: 100vh;
        display: flex;
        flex-direction: column;
    }

    .navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        background-color: #f5f5f5;
        border-bottom: 1px solid #ccc;
    }

    .navbar-left {
        display: flex;
        align-items: center;
    }

    .logo {
        height: 40px;
    }

    .navbar-right {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .nav-btn {
        background: none;
        border: none;
        font-size: 1rem;
        cursor: pointer;
        padding: 0.5rem 1rem;
        border-radius: 3px;
    }

    .nav-btn.active {
        background-color: #e0e0e0;
    }

    .nav-btn:hover:not(.active) {
        background-color: #f0f0f0;
    }

    .profile-btn {
        background: none;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        padding: 0.5rem;
    }

    .profile-btn.active {
        background-color: #e0e0e0;
    }

    .profile-btn:hover:not(.active) {
        background-color: #f0f0f0;
    }

    .content-area {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 1rem;
    }
</style>