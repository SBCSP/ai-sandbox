<script>
    import { onMount } from 'svelte';

    let userProfile = {
        name: '',
        email: '',
        joined: ''
    };

    onMount(async () => {
        try {
            const response = await fetch('http://localhost:5001/profile');
            if (response.ok) {
                userProfile = await response.json();
            } else {
                console.error('Failed to load profile:', response.status);
            }
        } catch (error) {
            console.error('Error fetching profile:', error);
        }
    });

    // Optional: Add a function to update profile
    async function updateProfile() {
        try {
            const response = await fetch('http://localhost:5001/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: userProfile.name,
                    email: userProfile.email
                })
            });
            if (response.ok) {
                const updatedProfile = await response.json();
                userProfile = updatedProfile;
                alert('Profile updated successfully!');
            } else {
                console.error('Failed to update profile:', response.status);
            }
        } catch (error) {
            console.error('Error updating profile:', error);
        }
    }
</script>

<div class="profile-container">
    <h1>Profile</h1>
    <p><strong>Name:</strong> <input bind:value={userProfile.name} /></p>
    <p><strong>Email:</strong> <input bind:value={userProfile.email} /></p>
    <p><strong>Joined:</strong> {userProfile.joined}</p>
    <button on:click={updateProfile}>Save Changes</button>
</div>

<style>
    .profile-container {
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

    input {
        padding: 0.5em;
        border: 1px solid #ccc;
        border-radius: 3px;
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