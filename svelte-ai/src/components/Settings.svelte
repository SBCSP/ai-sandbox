<script>
    import { onMount } from 'svelte';

    let settings = {
        theme: 'Light',
        notifications: true
    };

    onMount(async () => {
        try {
            const response = await fetch('http://localhost:5001/settings');
            if (response.ok) {
                settings = await response.json();
            } else {
                console.error('Failed to load settings:', response.status);
            }
        } catch (error) {
            console.error('Error fetching settings:', error);
        }
    });

    async function updateSettings() {
        try {
            const response = await fetch('http://localhost:5001/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    theme: settings.theme,
                    notifications: settings.notifications
                })
            });
            if (response.ok) {
                const updatedSettings = await response.json();
                settings = updatedSettings;
                alert('Settings updated successfully!');
            } else {
                console.error('Failed to update settings:', response.status);
            }
        } catch (error) {
            console.error('Error updating settings:', error);
        }
    }
</script>

<div class="settings-container">
    <h1>Settings</h1>
    <div class="setting-item">
        <label>
            Theme:
            <select bind:value={settings.theme}>
                <option>Light</option>
                <option>Dark</option>
            </select>
        </label>
    </div>
    <div class="setting-item">
        <label>
            <input type="checkbox" bind:checked={settings.notifications} />
            Enable Notifications
        </label>
    </div>
    <button on:click={updateSettings}>Save Settings</button>
</div>

<style>
    .settings-container {
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

    .setting-item {
        margin: 1em 0;
    }

    button {
        padding: 0.5em 1em;
        background-color: #ff3e00;
        color: #fff;
        border: none;
        border-radius: 3px;
        cursor: pointer;
        margin-top: 1em;
    }
</style>