// PWA Installation and Management
// Handles service worker registration, install prompts, and PWA features

class PWAManager {
    constructor() {
        this.deferredPrompt = null;
        this.isInstalled = false;
        this.swRegistration = null;

        this.init();
    }

    async init() {
        // Check if already installed
        this.checkInstallation();

        // Register service worker
        await this.registerServiceWorker();

        // Setup install prompt
        this.setupInstallPrompt();

        // Setup update checker
        this.setupUpdateChecker();

        // Request notification permission
        this.setupNotifications();
    }

    checkInstallation() {
        // Check if running as PWA
        if (window.matchMedia('(display-mode: standalone)').matches ||
            window.navigator.standalone === true) {
            this.isInstalled = true;
            console.log('[PWA] Running as installed app');
            document.body.classList.add('pwa-installed');
        }
    }

    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                this.swRegistration = await navigator.serviceWorker.register('/static/js/service-worker.js');
                console.log('[PWA] Service worker registered:', this.swRegistration);

                // Check for updates
                this.swRegistration.addEventListener('updatefound', () => {
                    console.log('[PWA] Update found!');
                    this.handleUpdate(this.swRegistration.installing);
                });

            } catch (error) {
                console.error('[PWA] Service worker registration failed:', error);
            }
        }
    }

    setupInstallPrompt() {
        // Capture install prompt event
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            console.log('[PWA] Install prompt available');

            // Show install button
            this.showInstallButton();
        });

        // Track installation
        window.addEventListener('appinstalled', () => {
            console.log('[PWA] App installed');
            this.isInstalled = true;
            this.hideInstallButton();
            this.deferredPrompt = null;

            // Track analytics
            if (typeof gtag !== 'undefined') {
                gtag('event', 'pwa_install', {
                    event_category: 'engagement',
                    event_label: 'PWA Installation'
                });
            }
        });
    }

    showInstallButton() {
        // Create install button if it doesn't exist
        let installBtn = document.getElementById('pwa-install-btn');

        if (!installBtn) {
            installBtn = document.createElement('button');
            installBtn.id = 'pwa-install-btn';
            installBtn.className = 'pwa-install-button';
            installBtn.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                <span>Install App</span>
            `;

            installBtn.addEventListener('click', () => this.promptInstall());

            // Add to header or create floating button
            const header = document.querySelector('header') || document.querySelector('.header-section');
            if (header) {
                header.appendChild(installBtn);
            } else {
                installBtn.classList.add('floating');
                document.body.appendChild(installBtn);
            }
        }

        installBtn.style.display = 'flex';
    }

    hideInstallButton() {
        const installBtn = document.getElementById('pwa-install-btn');
        if (installBtn) {
            installBtn.style.display = 'none';
        }
    }

    async promptInstall() {
        if (!this.deferredPrompt) {
            console.log('[PWA] No install prompt available');
            return;
        }

        // Show install prompt
        this.deferredPrompt.prompt();

        // Wait for user choice
        const { outcome } = await this.deferredPrompt.userChoice;
        console.log('[PWA] User choice:', outcome);

        if (outcome === 'accepted') {
            console.log('[PWA] User accepted install');
        } else {
            console.log('[PWA] User dismissed install');
        }

        this.deferredPrompt = null;
    }

    handleUpdate(worker) {
        worker.addEventListener('statechange', () => {
            if (worker.state === 'installed' && navigator.serviceWorker.controller) {
                // New version available
                this.showUpdateNotification();
            }
        });
    }

    showUpdateNotification() {
        // Create update notification
        const notification = document.createElement('div');
        notification.className = 'pwa-update-notification';
        notification.innerHTML = `
            <div class="update-content">
                <span>🎉 New version available!</span>
                <button id="pwa-update-btn" class="btn-update">Update Now</button>
                <button id="pwa-dismiss-btn" class="btn-dismiss">Later</button>
            </div>
        `;

        document.body.appendChild(notification);

        // Handle update
        document.getElementById('pwa-update-btn').addEventListener('click', () => {
            window.location.reload();
        });

        // Handle dismiss
        document.getElementById('pwa-dismiss-btn').addEventListener('click', () => {
            notification.remove();
        });

        // Auto-show
        setTimeout(() => notification.classList.add('show'), 100);
    }

    setupUpdateChecker() {
        // Check for updates every hour
        if (this.swRegistration) {
            setInterval(() => {
                this.swRegistration.update();
            }, 60 * 60 * 1000);
        }
    }

    async setupNotifications() {
        if (!('Notification' in window)) {
            console.log('[PWA] Notifications not supported');
            return;
        }

        // Check current permission
        if (Notification.permission === 'granted') {
            console.log('[PWA] Notifications already granted');
            await this.subscribeToPush();
        } else if (Notification.permission !== 'denied') {
            // Will request permission when user interacts
            console.log('[PWA] Notifications permission not set');
        }
    }

    async requestNotificationPermission() {
        const permission = await Notification.requestPermission();

        if (permission === 'granted') {
            console.log('[PWA] Notification permission granted');
            await this.subscribeToPush();
            return true;
        } else {
            console.log('[PWA] Notification permission denied');
            return false;
        }
    }

    async subscribeToPush() {
        if (!this.swRegistration) {
            console.log('[PWA] No service worker registration');
            return;
        }

        try {
            const subscription = await this.swRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(
                    // Replace with your VAPID public key
                    'YOUR_VAPID_PUBLIC_KEY_HERE'
                )
            });

            console.log('[PWA] Push subscription:', subscription);

            // Send subscription to server
            await fetch('/api/push-subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subscription)
            });

        } catch (error) {
            console.error('[PWA] Push subscription failed:', error);
        }
    }

    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\\-/g, '+')
            .replace(/_/g, '/');

        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);

        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }

        return outputArray;
    }

    // Share API
    async share(data) {
        if (navigator.share) {
            try {
                await navigator.share(data);
                console.log('[PWA] Shared successfully');
                return true;
            } catch (error) {
                console.log('[PWA] Share cancelled or failed:', error);
                return false;
            }
        } else {
            console.log('[PWA] Web Share API not supported');
            // Fallback to clipboard
            this.copyToClipboard(data.url || data.text);
            return false;
        }
    }

    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text);
            console.log('[PWA] Copied to clipboard');
        }
    }
}

// Initialize PWA manager
let pwaManager;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        pwaManager = new PWAManager();
    });
} else {
    pwaManager = new PWAManager();
}

// Export for use in other scripts
window.pwaManager = pwaManager;
