<script>
    import { onMount } from 'svelte';

    let settings = {
        theme: 'Light',
        notifications: true,
        llmServices: {
            ollama: { active: true },  // Default active since backend uses Ollama
            openai: { active: false },
            anthropic: { active: false },
            grok: { active: false }
        }
    };

    let isServicesDropdownOpen = false;

    onMount(async () => {
        try {
            const response = await fetch('http://localhost:5001/settings');
            if (response.ok) {
                const loadedSettings = await response.json();
                settings = { ...settings, ...loadedSettings }; // Merge with defaults
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
                    notifications: settings.notifications,
                    llmServices: settings.llmServices
                })
            });
            if (response.ok) {
                const updatedSettings = await response.json();
                settings = updatedSettings;
                alert('Settings updated successfully!');
            } else {
                console.error('Failed to update settings:', response.status);
                alert('Failed to update settings. Please try again.');
            }
        } catch (error) {
            console.error('Error updating settings:', error);
            alert('Failed to update settings. Please try again.');
        }
    }

    function toggleServicesDropdown() {
        isServicesDropdownOpen = !isServicesDropdownOpen;
    }

    function toggleService(serviceName) {
        settings.llmServices[serviceName].active = !settings.llmServices[serviceName].active;
        settings = settings; // Trigger reactivity
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

    <div class="setting-item">
        <button class="dropdown-toggle" on:click={toggleServicesDropdown}>
            LLM Services
            <span>{isServicesDropdownOpen ? '▲' : '▼'}</span>
        </button>
        {#if isServicesDropdownOpen}
            <div class="services-dropdown">
                {#each Object.entries(settings.llmServices) as [serviceName, serviceData]}
                    <div class="service-item">
                        <span>{serviceName}</span>
                        <label class="switch">
                            <input 
                                type="checkbox" 
                                checked={serviceData.active} 
                                on:change={() => toggleService(serviceName)}
                            />
                            <span class="slider"></span>
                        </label>
                    </div>
                {/each}
            </div>
        {/if}
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

    .dropdown-toggle {
        width: 100%;
        padding: 0.5em;
        background-color: #f5f5f5;
        border: 1px solid #ccc;
        border-radius: 3px;
        cursor: pointer;
        text-align: left;
        font-size: 1em;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .dropdown-toggle:hover {
        background-color: #e0e0e0;
    }

    .services-dropdown {
        margin-top: 0.5em;
        padding: 0.5em;
        border: 1px solid #ccc;
        border-radius: 3px;
        background-color: #fafafa;
    }

    .service-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.5em 0;
    }

    .service-item span {
        text-transform: capitalize;
    }

    /* Toggle Switch Styles */
    .switch {
        position: relative;
        display: inline-block;
        width: 40px;
        height: 20px;
    }

    .switch input {
        opacity: 0;
        width: 0;
        height: 0;
    }

    .slider {
        position: absolute;
        cursor: pointer;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: #ccc;
        transition: .4s;
        border-radius: 20px;
    }

    .slider:before {
        position: absolute;
        content: "";
        height: 16px;
        width: 16px;
        left: 2px;
        bottom: 2px;
        background-color: white;
        transition: .4s;
        border-radius: 50%;
    }

    input:checked + .slider {
        background-color: #ff3e00;
    }

    input:checked + .slider:before {
        transform: translateX(20px);
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

    button:hover {
        background-color: #e63900;
    }
</style>