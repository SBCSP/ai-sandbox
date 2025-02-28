<script>
    import { onMount } from "svelte";

    export let availableChats = []; // Props for chat history
    export let onSelectChat; // Callback to load a selected chat
    export let loading = false; // Props for loading state

    // Function to delete a chat by chat_id
    async function deleteChat(chatId) {
        if (loading) return; // Prevent deletion while loading
        if (
            !confirm(
                `Are you sure you want to delete the chat "${availableChats.find((chat) => chat.chat_id === chatId)?.last_message}"?`,
            )
        ) {
            return; // Cancel if user doesn't confirm
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
            // Refresh the chat history after deletion
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

    // Load chat history on mount
    onMount(() => {
        loadChatHistory();
    });
</script>

<div class="sidebar">
    <h2>Chat History</h2>
    <div class="chat-list">
        {#if loading}
            <p>Loading chats...</p>
        {:else if availableChats.length === 0}
            <p>No chats available.</p>
        {:else}
            {#each availableChats as chat}
                <button
                    class="chat-item"
                    on:click={() => onSelectChat(chat.chat_id)}
                    disabled={loading}
                >
                    <span class="chat-text">
                        {chat.last_message.slice(0, 10) +
                            (chat.last_message.length > 10 ? "..." : "")}
                        ({new Date(chat.timestamp).toLocaleString()})
                    </span>
                    <span
                        class="delete-button"
                        on:click|stopPropagation={() =>
                            deleteChat(chat.chat_id)}
                        title="Delete this chat"
                    >
                        ×
                    </span>
                </button>
            {/each}
        {/if}
    </div>
    <button on:click={() => onSelectChat("")} disabled={loading}
        >Clear Selection</button
    >
</div>

<style>
    .sidebar {
        width: 300px; /* Fixed width for sidebar */
        height: 100vh; /* Full viewport height */
        background-color: #f5f5f5; /* Light gray background */
        border-right: 1px solid #ccc; /* Divider line */
        padding: 1em;
        overflow-y: auto; /* Scroll if content overflows */
    }

    h2 {
        margin-top: 0;
        color: #333;
        font-size: 1.2em;
    }

    .chat-list {
        margin-top: 1em;
    }

    .chat-item {
        position: relative;
        width: 100%;
        padding: 0.5em;
        margin: 0.2em 0;
        background-color: #fff;
        border: 1px solid #c06868;
        border-radius: 3px;
        text-align: left;
        cursor: pointer;
        overflow-wrap: break-word; /* Handle long text */
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
        margin-right: 0.5em; /* Space for the delete button */
        white-space: nowrap; /* Prevent text wrapping */
        overflow: hidden; /* Hide overflow */
        text-overflow: ellipsis; /* Show ellipsis for truncated text */
    }

    .delete-button {
        padding: 0.2em 0.4em;
        background-color: #ff3e00;
        color: #fff;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        font-size: 0.8em;
        opacity: 0.8;
        transition: opacity 0.2s;
        display: none; /* Hidden by default */
    }

    .delete-button:hover:not(:disabled) {
        opacity: 1;
    }

    .delete-button:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .chat-item:hover .delete-button {
        display: inline-flex; /* Show on hover */
    }

    button {
        padding: 0.5em 1em;
        background-color: #ff3e00;
        color: rgb(87, 77, 77);
        border: none;
        border-radius: 3px;
        cursor: pointer;
        margin-top: 1em;
        width: 100%;
    }

    button:disabled {
        background-color: #ccc;
        cursor: not-allowed;
    }
</style>
