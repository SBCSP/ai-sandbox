<!-- AppConfig.svelte -->
<script>
    import { onMount } from 'svelte';

    // Configuration state
    let config = {
        apiEndpoint: 'http://localhost:5001',
        maxChats: 100,
        theme: 'light',
        autoSave: true
    };

    // Object Storage state
    let objectStorage = {
        provider: 'minio',
        endpoint_url: '',
        access_key: '',
        secret_key: '',
        bucket_name: 'ai-sandbox' // Default bucket name
    };

    let isLoading = false;
    let error = null;
    let success = null;

    onMount(async () => {
        await loadConfig();
        await loadObjectStorage();
    });

    // Fetch general config from backend (placeholder for future use)
    async function loadConfig() {
        isLoading = true;
        error = null;
        try {
            const response = await fetch(`${config.apiEndpoint}/config`);
            if (!response.ok && response.status !== 404) { // Allow 404 for now
                throw new Error('Failed to load configuration');
            }
            const data = await response.json();
            config = { ...config, ...data };
        } catch (err) {
            error = err.message;
        } finally {
            isLoading = false;
        }
    }

    // Fetch object storage settings
    async function loadObjectStorage() {
        isLoading = true;
        error = null;
        try {
            const response = await fetch(`${config.apiEndpoint}/object-storage`);
            if (!response.ok) {
                // If the response is not OK (e.g., 404 or 500), use default values
                objectStorage = {
                    provider: 'minio',
                    endpoint_url: '',
                    access_key: '',
                    secret_key: '',
                    bucket_name: 'ai-sandbox' // Default bucket name
                };
                return; // No error shown, just use defaults
            }
            objectStorage = await response.json();
            console.log('Loaded object storage settings:', objectStorage);
        } catch (err) {
            // Handle network errors or other issues by using default values
            error = `Failed to load object storage settings: ${err.message}`;
            objectStorage = {
                provider: 'minio',
                endpoint_url: '',
                access_key: '',
                secret_key: '',
                bucket_name: 'ai-sandbox' // Default bucket name
            };
            console.error('Error loading object storage settings:', err);
        } finally {
            isLoading = false;
        }
    }

    // Save general config (placeholder for future use)
    async function saveConfig() {
        isLoading = true;
        error = null;
        success = null;
        try {
            const response = await fetch(`${config.apiEndpoint}/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            if (!response.ok) {
                throw new Error('Failed to save configuration');
            }
            success = 'Configuration saved successfully';
        } catch (err) {
            error = err.message;
        } finally {
            isLoading = false;
        }
    }

    // Save object storage settings
    async function saveObjectStorage() {
        isLoading = true;
        error = null;
        success = null;
        try {
            console.log('Saving object storage settings:', objectStorage);
            const response = await fetch(`${config.apiEndpoint}/object-storage`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(objectStorage)
            });
            if (!response.ok) {
                throw new Error('Failed to save object storage settings: ' + (await response.text()));
            }
            success = 'Object storage settings saved successfully';
            await loadObjectStorage(); // Refresh after save
        } catch (err) {
            error = err.message;
            console.error('Error saving object storage settings:', err);
        } finally {
            isLoading = false;
        }
    }

    // Delete object storage settings
    async function deleteObjectStorage() {
        if (!confirm('Are you sure you want to delete object storage settings?')) return;
        isLoading = true;
        error = null;
        success = null;
        try {
            const response = await fetch(`${config.apiEndpoint}/object-storage`, {
                method: 'DELETE'
            });
            if (!response.ok) {
                throw new Error('Failed to delete object storage settings');
            }
            success = 'Object storage settings deleted successfully';
            objectStorage = { 
                provider: 'minio', 
                endpoint_url: '', 
                access_key: '', 
                secret_key: '', 
                bucket_name: 'ai-sandbox' // Default bucket name
            };
            await loadObjectStorage(); // Refresh after delete
        } catch (err) {
            error = err.message;
        } finally {
            isLoading = false;
        }
    }
</script>

<div class="app-config">
    <h1>Application Configuration</h1>

    {#if isLoading}
        <p class="loading">Loading...</p>
    {:else if error}
        <p class="error">{error}</p>
    {:else}
        <!-- General Configuration -->
        <form on:submit|preventDefault={saveConfig}>
            <div class="form-group">
                <label for="apiEndpoint">API Endpoint:</label>
                <input id="apiEndpoint" type="text" bind:value={config.apiEndpoint} disabled={isLoading} />
            </div>
            <div class="form-group">
                <label for="maxChats">Max Chats:</label>
                <input id="maxChats" type="number" bind:value={config.maxChats} disabled={isLoading} />
            </div>
            <div class="form-group">
                <label for="theme">Theme:</label>
                <select id="theme" bind:value={config.theme} disabled={isLoading}>
                    <option value="light">Light</option>
                    <option value="dark">Dark</option>
                </select>
            </div>
            <div class="form-group checkbox">
                <label>
                    <input type="checkbox" bind:checked={config.autoSave} disabled={isLoading} />
                    Auto Save
                </label>
            </div>
            <button type="submit" disabled={isLoading}>
                {isLoading ? 'Saving...' : 'Save Configuration'}
            </button>
        </form>

        <!-- Object Storage Configuration -->
        <h2>Object Storage</h2>
        <form on:submit|preventDefault={saveObjectStorage}>
            <div class="form-group">
                <label for="provider">Provider:</label>
                <select id="provider" bind:value={objectStorage.provider} disabled={isLoading}>
                    <option value="minio">MinIO</option>
                    <option value="s3">AWS S3</option>
                </select>
            </div>
            <div class="form-group">
                <label for="endpoint_url">Endpoint URL:</label>
                <input id="endpoint_url" type="text" bind:value={objectStorage.endpoint_url} disabled={isLoading} />
            </div>
            <div class="form-group">
                <label for="access_key">Access Key:</label>
                <input id="access_key" type="text" bind:value={objectStorage.access_key} disabled={isLoading} />
            </div>
            <div class="form-group">
                <label for="secret_key">Secret Key:</label>
                <input id="secret_key" type="password" bind:value={objectStorage.secret_key} disabled={isLoading} />
            </div>
            <div class="form-group">
                <label for="bucket_name">Bucket Name:</label>
                <input id="bucket_name" type="text" bind:value={objectStorage.bucket_name} disabled={isLoading} />
            </div>
            <button type="submit" disabled={isLoading}>
                {isLoading ? 'Saving...' : 'Save Object Storage'}
            </button>
            <button type="button" on:click={deleteObjectStorage} disabled={isLoading}>
                Delete
            </button>
        </form>

        {#if success}
            <p class="success">{success}</p>
        {/if}
    {/if}
</div>

<style>
    .app-config {
        padding: 2rem;
        max-width: 600px;
        margin: 0 auto;
    }
    h1, h2 {
        color: #ff3e00;
        margin-bottom: 1.5rem;
    }
    h2 {
        margin-top: 2rem;
    }
    .form-group {
        margin-bottom: 1rem;
    }
    .form-group.checkbox {
        display: flex;
        align-items: center;
    }
    label {
        display: block;
        margin-bottom: 0.5rem;
        color: #333;
    }
    input, select {
        width: 100%;
        padding: 0.5rem;
        border: 1px solid #c06868;
        border-radius: 4px;
        font-size: 1rem;
    }
    button {
        background-color: #ff3e00;
        color: white;
        padding: 0.75rem 1.5rem;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 1rem;
        margin-top: 1rem;
        margin-right: 0.5rem;
    }
    button:disabled {
        background-color: #ccc;
        cursor: not-allowed;
    }
    .loading {
        color: #666;
        font-style: italic;
    }
    .error {
        color: #ff3e00;
        margin: 1rem 0;
    }
    .success {
        color: #28a745;
        margin: 1rem 0;
    }
</style>