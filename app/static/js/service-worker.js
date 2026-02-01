// Service Worker for Football Predictor Pro PWA
// Provides offline support, caching, and background sync

const CACHE_NAME = 'football-predictor-v1';
const RUNTIME_CACHE = 'football-predictor-runtime-v1';

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/predict',
    '/live-predictions',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/js/three-scene.js',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('[SW] Service worker installed successfully');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Installation failed:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    
    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => {
                            return name !== CACHE_NAME && name !== RUNTIME_CACHE;
                        })
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Service worker activated');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip cross-origin requests
    if (url.origin !== location.origin) {
        return;
    }
    
    // API requests - network first, cache fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(request));
        return;
    }
    
    // Static assets - cache first, network fallback
    event.respondWith(cacheFirst(request));
});

// Cache-first strategy
async function cacheFirst(request) {
    const cache = await caches.open(CACHE_NAME);
    const cached = await cache.match(request);
    
    if (cached) {
        console.log('[SW] Serving from cache:', request.url);
        return cached;
    }
    
    try {
        const response = await fetch(request);
        
        // Cache successful responses
        if (response.ok) {
            cache.put(request, response.clone());
        }
        
        return response;
    } catch (error) {
        console.error('[SW] Fetch failed:', error);
        
        // Return offline page if available
        const offlinePage = await cache.match('/offline.html');
        if (offlinePage) {
            return offlinePage;
        }
        
        throw error;
    }
}

// Network-first strategy
async function networkFirst(request) {
    const cache = await caches.open(RUNTIME_CACHE);
    
    try {
        const response = await fetch(request);
        
        // Cache successful API responses
        if (response.ok) {
            cache.put(request, response.clone());
        }
        
        return response;
    } catch (error) {
        console.log('[SW] Network failed, trying cache:', request.url);
        
        const cached = await cache.match(request);
        if (cached) {
            return cached;
        }
        
        throw error;
    }
}

// Background sync for predictions
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync:', event.tag);
    
    if (event.tag === 'sync-predictions') {
        event.waitUntil(syncPredictions());
    }
});

async function syncPredictions() {
    try {
        // Sync saved predictions when back online
        const db = await openDatabase();
        const predictions = await getPendingPredictions(db);
        
        for (const prediction of predictions) {
            await fetch('/api/save-prediction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(prediction)
            });
        }
        
        console.log('[SW] Predictions synced successfully');
    } catch (error) {
        console.error('[SW] Sync failed:', error);
    }
}

// Push notifications for live scores
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');
    
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Football Predictor Pro';
    const options = {
        body: data.body || 'New update available',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        vibrate: [200, 100, 200],
        data: data,
        actions: [
            {
                action: 'view',
                title: 'View',
                icon: '/static/icons/view.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/static/icons/close.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked:', event.action);
    
    event.notification.close();
    
    if (event.action === 'view') {
        event.waitUntil(
            clients.openWindow(event.notification.data.url || '/')
        );
    }
});

// Helper: Open IndexedDB
function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('FootballPredictorDB', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('predictions')) {
                db.createObjectStore('predictions', { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

// Helper: Get pending predictions
async function getPendingPredictions(db) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['predictions'], 'readonly');
        const store = transaction.objectStore('predictions');
        const request = store.getAll();
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

console.log('[SW] Service worker loaded');
