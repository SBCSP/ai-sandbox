<script>
    import { onMount } from 'svelte';

    let settings = [];
    let newKey = '';
    let newValue = '';
    let editingKey = null;
    let editingValue = '';
    let loading = false;
    let error = '';

    // Fetch global settings from the backend
    async function fetchSettings() {
        loading = true;
        error = '';
        try {
            const response = await fetch('http://localhost:5001/admin/global_settings');
            if (response.ok) {
                const data = await response.json();
                settings = Object.entries(data).map(([key, value]) => ({ key, value }));
            } else {
                error = 'Failed to load settings';
            }
        } catch (err) {
            error = `Error fetching settings: ${err.message}`;
        } finally {
            loading = false;
        }
    }

    // Add a new setting
    async function addSetting() {
        if (!newKey.trim() || !newValue.trim()) {
            error = 'Key and value are required';
            return;
        }

        loading = true;
        error = '';
        try {
            const response = await fetch('http://localhost:5001/admin/global_settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: newKey.trim(), value: newValue.trim() })
            });
            if (response.ok) {
                await fetchSettings(); // Refresh the list
                newKey = '';
                newValue = '';
            } else {
                error = 'Failed to add setting';
            }
        } catch (err) {
            error = `Error adding setting: ${err.message}`;
        } finally {
            loading = false;
        }
    }

    // Edit a setting
    async function editSetting(key) {
        editingKey = key;
        const setting = settings.find(s => s.key === key);
        editingValue = setting.value;
    }

    // Save edited setting
    async function saveEdit() {
        if (!editingKey || !editingValue.trim()) {
            error = 'Value is required for editing';
            return;
        }

        loading = true;
        error = '';
        try {
            const response = await fetch(`http://localhost:5001/admin/global_settings/${encodeURIComponent(editingKey)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value: editingValue.trim() })
            });
            if (response.ok) {
                await fetchSettings(); // Refresh the list
                editingKey = null;
                editingValue = '';
            } else {
                error = 'Failed to update setting';
            }
        } catch (err) {
            error = `Error updating setting: ${err.message}`;
        } finally {
            loading = false;
        }
    }

    // Delete a setting
    async function deleteSetting(key) {
        if (!confirm(`Are you sure you want to delete the setting '${key}'?`)) {
            return;
        }

        loading = true;
        error = '';
        try {
            const response = await fetch(`http://localhost:5001/admin/global_settings/${encodeURIComponent(key)}`, {
                method: 'DELETE'
            });
            if (response.ok) {
                await fetchSettings(); // Refresh the list
            } else {
                error = 'Failed to delete setting';
            }
        } catch (err) {
            error = `Error deleting setting: ${err.message}`;
        } finally {
            loading = false;
        }
    }

    // Cancel editing
    function cancelEdit() {
        editingKey = null;
        editingValue = '';
    }

    onMount(fetchSettings);
</script>

<div class="admin-container">
    <h1>Admin Settings</h1>
    {#if loading}
        <p>Loading...</p>
    {:else if error}
        <p class="error">{error}</p>
    {:else}
        <div class="settings-list">
            {#each settings as setting}
                <div class="setting-item">
                    <span class="key">{setting.key}</span>
                    {#if editingKey === setting.key}
                        <input bind:value={editingValue} class="edit-input" />
                        <button on:click={saveEdit} class="save-btn">Save</button>
                        <button on:click={cancelEdit} class="cancel-btn">Cancel</button>
                    {:else}
                        <span class="value">{setting.value}</span>
                        <button on:click={() => editSetting(setting.key)} class="edit-btn">Edit</button>
                        <button on:click={() => deleteSetting(setting.key)} class="delete-btn">Delete</button>
                    {/if}
                </div>
            {/each}
        </div>

        <div class="add-setting">
            <input bind:value={newKey} placeholder="Key" class="input-field" />
            <input bind:value={newValue} placeholder="Value" class="input-field" />
            <button on:click={addSetting} disabled={loading} class="add-btn">Add Setting</button>
        </div>
    {/if}
</div>

<style>
    .admin-container {
        padding: 1em;
        background-color: #fff;
        border: 1px solid #ccc;
        border-radius: 3px;
        height: 100%;
        overflow-y: auto;
    }

    h1 {
        color: #333;
        margin-top: 0;
    }

    .settings-list {
        margin-top: 1em;
    }

    .setting-item {
        display: flex;
        align-items: center;
        gap: 0.5em;
        margin: 0.5em 0;
        padding: 0.5em;
        background-color: #f9f9f9;
        border: 1px solid #ccc;
        border-radius: 3px;
    }

    .key, .value {
        flex: 1;
        word-wrap: break-word;
    }

    .edit-input {
        flex: 1;
        padding: 0.5em;
        border: 1px solid #ccc;
        border-radius: 3px;
    }

    button {
        padding: 0.5em 1em;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        margin-left: 0.5em;
    }

    .edit-btn {
        background-color: #4CAF50;
        color: white;
    }

    .save-btn {
        background-color: #2196F3;
        color: white;
    }

    .cancel-btn {
        background-color: #f44336;
        color: white;
    }

    .delete-btn {
        background-color: #ff3e00;
        color: white;
    }

    .add-btn {
        background-color: #ff3e00;
        color: white;
    }

    .add-btn:disabled {
        background-color: #ccc;
        cursor: not-allowed;
    }

    .add-setting {
        margin-top: 1em;
        display: flex;
        gap: 0.5em;
    }

    .input-field {
        flex: 1;
        padding: 0.5em;
        border: 1px solid #ccc;
        border-radius: 3px;
    }

    .error {
        color: #f44336;
        margin-top: 1em;
    }
</style>