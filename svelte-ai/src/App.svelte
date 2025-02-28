<script>
	import { marked } from "marked";
	import { onMount } from "svelte";
	import ChatSidebar from "./components/ChatSidebar.svelte"; // Import the sidebar component

	let message = "";
	let currentResponse = "";
	let chatHistory = [];
	let loading = false;
	let chatContainer;
	let fileInput;
	let chatId = localStorage.getItem("chatId") || ""; // Load or initialize chat_id from localStorage
	let availableChats = []; // Store list of past chats

	function parseMarkdown(text) {
		return marked.parse(text, { breaks: true, gfm: true });
	}

	// Generate or reuse chat_id, store in localStorage
	function initializeChatId() {
		if (!chatId) {
			chatId = crypto.randomUUID(); // Use modern UUID (Node.js or modern browsers)
			localStorage.setItem("chatId", chatId); // Persist for future sessions
		}
		return chatId;
	}

	// Load available chats from backend
	async function loadChatHistory() {
		try {
			const res = await fetch("http://localhost:5001/history");
			const data = await res.json();
			availableChats = data.chats || [];
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
							: undefined, // Handle images later
				}));
				localStorage.setItem("chatId", chatId); // Update current chat_id
				this.chatId = chatId; // Update state
			}
		} catch (error) {
			console.error("Error loading chat:", error);
		}
	}

	// Clear current chat (delete from MongoDB and reset locally)
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
				await loadChatHistory(); // Refresh available chats
			}
		} catch (error) {
			console.error("Error clearing chat:", error);
		}
	}

	// Start a new chat (reset chat_id)
	function startNewChat() {
		chatHistory = [];
		localStorage.removeItem("chatId");
		chatId = crypto.randomUUID();
		localStorage.setItem("chatId", chatId);
		loadChatHistory(); // Refresh available chats
	}

	// Handle text message submission
	async function handleSubmit(event) {
		event.preventDefault();
		if (!message.trim()) return;

		const chatId = initializeChatId(); // Ensure chat_id exists
		chatHistory = [...chatHistory, { role: "user", content: message }];
		loading = true;
		currentResponse = "";

		try {
			const res = await fetch("http://localhost:5001/chat", {
				method: "POST",
				headers: {
					"Content-Type": "application/x-www-form-urlencoded",
				},
				body: new URLSearchParams({
					message,
					chat_id: chatId, // Send chat_id with request
				}),
			});

			if (!res.ok) {
				throw new Error(`HTTP error! Status: ${res.status}`);
			}

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
							chatHistory = [
								...chatHistory,
								{ role: "ai", content: currentResponse },
							];
							currentResponse = "";
							loading = false;
						} else {
							currentResponse += data + "\n";
						}
					}
				}
			}
		} catch (error) {
			console.error("Fetch streaming error:", error);
			currentResponse = `Error: ${error.message}`;
			chatHistory = [
				...chatHistory,
				{ role: "ai", content: currentResponse },
			];
			loading = false;
		}

		message = "";
	}

	// Handle image upload submission with streaming
	async function handleImageSubmit(event) {
		event.preventDefault();
		if (!fileInput.files || fileInput.files.length === 0) return;

		const file = fileInput.files[0];
		const imageUrl = URL.createObjectURL(file); // Create a local URL for preview
		const chatId = initializeChatId(); // Ensure chat_id exists
		const formData = new FormData();
		formData.append("file", file);
		formData.append("chat_id", chatId); // Send chat_id with request

		chatHistory = [
			...chatHistory,
			{
				role: "user",
				content: `Uploaded image: ${file.name}`,
				image: imageUrl,
			},
		];
		loading = true;
		currentResponse = "";

		try {
			const res = await fetch("http://localhost:5001/image", {
				method: "POST",
				body: formData,
			});

			if (!res.ok) {
				throw new Error(`HTTP error! Status: ${res.status}`);
			}

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
							chatHistory = [
								...chatHistory,
								{ role: "ai", content: currentResponse },
							];
							currentResponse = "";
							loading = false;
						} else {
							currentResponse += data + "\n";
						}
					}
				}
			}
		} catch (error) {
			console.error("Image streaming error:", error);
			currentResponse = `Error: ${error.message}`;
			chatHistory = [
				...chatHistory,
				{ role: "ai", content: currentResponse },
			];
			loading = false;
		}

		fileInput.value = ""; // Reset file input
	}

	function autoScroll() {
		if (!chatContainer) return;
		const { scrollTop, scrollHeight, clientHeight } = chatContainer;
		const isNearBottom = scrollTop + clientHeight >= scrollHeight - 50;
		if (isNearBottom) {
			requestAnimationFrame(() => {
				chatContainer.scrollTop = chatContainer.scrollHeight;
			});
		}
	}

	$: (chatHistory.length || currentResponse || loading) && autoScroll();

	// Load chats on mount
	onMount(async () => {
		await loadChatHistory();
		if (chatId) {
			await loadChat(chatId); // Load current chat if it exists
		}
	});
</script>

<main>
	<div class="layout">
		<ChatSidebar {availableChats} onSelectChat={loadChat} {loading} />
		<div class="chat-area">
			<h1>AI Sandbox</h1>
			<div class="chat-controls">
				<button on:click={clearChat} disabled={loading || !chatId}
					>Clear Chat</button
				>
				<button on:click={startNewChat} disabled={loading}
					>New Chat</button
				>
			</div>
			<div class="chat-container" bind:this={chatContainer}>
				{#each chatHistory as { role, content, image }, i}
					<div class="message {role}">
						<strong>{role === "user" ? "You" : "AI"}:</strong>
						{#if role === "ai"}
							<span class="content"
								>{@html parseMarkdown(content)}</span
							>
						{:else}
							<span class="content">{content}</span>
							{#if image}
								<img
									src={image}
									alt="Uploaded image"
									class="preview"
								/>
							{/if}
						{/if}
					</div>
				{/each}
				{#if currentResponse}
					<div class="message ai">
						<strong>AI:</strong>
						<span class="content"
							>{@html parseMarkdown(currentResponse)}</span
						>
					</div>
				{/if}
				{#if loading && !currentResponse}
					<div class="message ai">
						<strong>AI:</strong>
						<span class="content">Processing...</span>
					</div>
				{/if}
			</div>
			<form on:submit={handleSubmit}>
				<input
					type="text"
					bind:value={message}
					placeholder="Type a message"
					disabled={loading}
				/>
				<label
					for="image-upload"
					class="image-button"
					title="Upload an image"
				>
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
</main>

<style>
	.layout {
		display: flex;
		height: 100vh;
	}

	.sidebar {
		width: 300px; /* Fixed width for sidebar */
		height: 100vh; /* Full viewport height */
		background-color: #f5f5f5; /* Light gray background */
		border-right: 1px solid #ccc; /* Divider line */
		padding: 1em;
		overflow-y: auto; /* Scroll if content overflows */
	}

	.chat-area {
		flex: 1;
		display: flex;
		flex-direction: column;
		padding: 1em;
		width: calc(70% - 300px); /* Adjust 70% width to account for sidebar */
	}

	h1 {
		color: #ff3e00;
		text-align: center;
		margin-bottom: 0.5em;
	}

	.chat-controls {
		display: flex;
		gap: 0.5em;
		margin-bottom: 0.5em;
	}

	.chat-controls button {
		padding: 0.5em 1em;
		border: 1px solid #ccc;
		border-radius: 3px;
		background-color: #fff;
		cursor: pointer;
	}

	.chat-controls button:disabled {
		background-color: #ccc;
		cursor: not-allowed;
	}

	.chat-container {
		flex: 1;
		overflow-y: auto;
		border: 1px solid #ccc;
		padding: 1em;
		background-color: #f9f9f9;
		scroll-behavior: smooth;
		margin-bottom: 1em;
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

	.content :global(p) {
		margin: 0.5em 0;
	}

	.content :global(pre) {
		background: #f5f5f5;
		padding: 0.5em;
		border-radius: 3px;
		overflow-x: auto;
	}

	.content :global(code) {
		font-family: monospace;
	}

	.content :global(ul),
	.content :global(ol) {
		margin: 0.5em 0;
		padding-left: 1.5em;
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
		position: sticky;
		bottom: 0;
		padding: 0.5em 0;
		background-color: #fff;
		z-index: 10;
		align-items: center;
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
		color: #a56161;
		border: none;
		border-radius: 3px;
		cursor: pointer;
	}

	button:disabled {
		background-color: #a56161;
		cursor: not-allowed;
	}
</style>
