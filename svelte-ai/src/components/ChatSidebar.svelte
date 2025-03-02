<script>
    import { onMount } from "svelte";

    export let availableChats = [];
    export let onSelectChat;
    export let loading = false;
    export let onSelectOption;

    let sidebarCollapsed = false;

    // Function to delete a chat by chat_id
    async function deleteChat(chatId) {
        if (loading) return;
        if (
            !confirm(
                `Are you sure you want to delete the chat "${availableChats.find((chat) => chat.chat_id === chatId)?.title}"?`,
            )
        ) {
            return;
        }

        try {
            const res = await fetch(`http://localhost:5001/history/${chatId}`, {
                method: "DELETE",
            });

            if (!res.ok) {
                throw new Error(`HTTP error! Status: ${res.status}`);
            }

            const data = await res.json();
            console.log("Chat deleted:", data.message);
            await loadChatHistory();
        } catch (error) {
            console.error("Error deleting chat:", error);
            alert(`Failed to delete chat: ${error.message}`);
        }
    }

    // Load chat history
    async function loadChatHistory() {
        try {
            const res = await fetch("http://localhost:5001/history");
            const data = await res.json();
            availableChats = data.chats || [];
        } catch (error) {
            console.error("Error loading chat history:", error);
            alert(`Failed to load chat history: ${error.message}`);
        }
    }

    // Toggle sidebar collapse state
    function toggleSidebar() {
        sidebarCollapsed = !sidebarCollapsed;
    }

    // Load chat history on mount
    onMount(() => {
        loadChatHistory();
    });
</script>

<div class="sidebar" class:collapsed={sidebarCollapsed}>
    <div class="header-row">
        <h1 class="logo">SandboxAI</h1>
        <button class="toggle-button" on:click={toggleSidebar}>
            {sidebarCollapsed ? "▶" : "◀"}
        </button>
    </div>

    {#if !sidebarCollapsed}
        <h2 class="section-header">Chats</h2>
        <div class="chat-list">
            {#if loading}
                <p class="loading-text">Loading chats...</p>
            {:else if availableChats.length === 0}
                <p class="no-chats-text">No chats available.</p>
            {:else}
                {#each availableChats as chat}
                    <div class="chat-item" on:click={() => onSelectChat(chat.chat_id)}>
                        <span class="chat-text">{chat.title}</span>
                        <button
                            class="delete-button"
                            on:click|stopPropagation={() => deleteChat(chat.chat_id)}
                            disabled={loading}
                            aria-label={`Delete chat '${chat.title}'`}
                        >
                            ×
                        </button>
                    </div>
                {/each}
            {/if}
        </div>
        <button on:click={() => onSelectChat("")} disabled={loading} class="clear-button">Clear Selection</button>

        <h2 class="section-header">Administrator</h2>
        <div class="options-list">
            <div class="option-item" on:click={() => onSelectOption("Settings")}>Settings</div>
            <div class="option-item" on:click={() => onSelectOption("AppConfig")}>App Configuration</div>
        </div>

        <h2 class="section-header">User</h2>
        <div class="options-list">
            <div class="option-item" on:click={() => onSelectOption("Profile")}>Profile</div>
        </div>
    {/if}
</div>

<style>
    .sidebar {
        position: relative;
        width: 300px;
        height: 100vh;
        background-color: #f5f5f5;
        border-right: 1px solid #ccc;
        padding: 1em;
        overflow-y: auto;
        transition: width 0.3s ease;
    }

    .sidebar.collapsed {
        width: 40px;
        padding: 0;
    }

    .header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1em;
    }

    .logo {
        margin: 0;
        color: #ff3e00;
        font-size: 1.5em;
        font-weight: bold;
    }

    .toggle-button {
        width: 30px;
        height: 30px;
        font-size: 1.2em;
        border: none;
        background-color: #ddd;
        cursor: pointer;
        border-radius: 3px;
        z-index: 1;
    }

    .toggle-button:hover {
        background-color: #ccc;
    }

    .section-header {
        margin-top: 1.5em;
        margin-bottom: 0.5em;
        color: #333;
        font-size: 1.2em;
    }

    .chat-list {
        margin-top: 0.5em;
    }

    .chat-item {
        width: 100%;
        padding: 0.7em;
        margin: 0.3em 0;
        background-color: #fff;
        border: 1px solid #c06868;
        border-radius: 5px;
        text-align: left;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: background-color 0.2s;
    }

    .chat-item:hover:not(:disabled) {
        background-color: #93b1d5;
    }

    .chat-item:disabled {
        background-color: #3f4a57;
        cursor: not-allowed;
    }

    .chat-text {
        flex: 1;
        margin-right: 1em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .delete-button {
        padding: 0.3em 0.5em;
        background-color: #ff3e00;
        color: #fff;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        font-size: 0.9em;
        opacity: 0;
        transition: opacity 0.2s;
        width: 1.8em;
        height: 1.8em;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .delete-button:hover:not(:disabled) {
        opacity: 1;
    }

    .delete-button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .chat-item:hover .delete-button {
        opacity: 1;
    }

    .clear-button {
        padding: 0.6em 1em;
        background-color: #ff3e00;
        color: #fff;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        margin-top: 1em;
        width: 100%;
    }

    .clear-button:disabled {
        background-color: #ccc;
        cursor: not-allowed;
    }

    .options-list {
        margin-top: 0.5em;
    }

    .option-item {
        padding: 0.7em;
        margin: 0.3em 0;
        background-color: #fff;
        border: 1px solid #c06868;
        border-radius: 5px;
        text-align: left;
        cursor: pointer;
        transition: background-color 0.2s;
    }

    .option-item:hover {
        background-color: #93b1d5;
    }

    .loading-text,
    .no-chats-text {
        color: #666;
        font-style: italic;
    }
</style>