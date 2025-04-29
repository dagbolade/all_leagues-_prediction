// static/js/live-scores.js

class LiveScoresManager {
    constructor() {
        this.updateInterval = 180000; // Update every minute
        this.container = document.getElementById('liveScores');
        this.init();
    }

    async init() {
        await this.updateScores();
        setInterval(() => this.updateScores(), this.updateInterval);
    }

    async updateScores() {
    try {
        this.showLoading();
        console.log("Fetching live scores...");

        const response = await fetch('/api/live-scores');
        const text = await response.text(); // Get raw response text first
        console.log("Raw response:", text);

        let data;
        try {
            data = JSON.parse(text);
        } catch (e) {
            throw new Error("Failed to parse API response");
        }

        if (data.error) {
            throw new Error(data.message || data.error);
        }

        this.displayScores(data.matches || []);
        this.updateLastUpdated();

    } catch (error) {
        console.error("Error fetching scores:", error);
        this.showError(`Error loading live scores: ${error.message}`);
    }
}

    showLoading() {
        if (!this.container) return;
        this.container.innerHTML = `
            <div class="text-center p-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
    }

    showError(message) {
        if (!this.container) return;
        this.container.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-circle"></i>
                Error loading live scores: ${message}
            </div>
        `;
    }

   displayScores(matches) {
    if (!this.container) return;

    if (!matches.length) {
        this.container.innerHTML = `
            <div class="text-center p-4">
                <i class="fas fa-calendar-times"></i>
                <p class="mb-0">No live matches currently</p>
            </div>
        `;
        return;
    }

    this.container.innerHTML = matches.map(match => {
        const homeScore = match.score?.fullTime?.home ?? '-';
        const awayScore = match.score?.fullTime?.away ?? '-';

        return `
            <div class="live-match-card">
                <div class="match-header">
                    <span class="competition-name">${match.competition?.name || ''}</span>
                    <span class="match-minute">${this.getMatchMinute(match)}</span>
                </div>
                <div class="match-teams">
                    <div class="team home">
                        <span class="team-name">${match.homeTeam.name}</span>
                        <span class="score">${homeScore}</span>
                    </div>
                    <div class="score-divider">-</div>
                    <div class="team away">
                        <span class="team-name">${match.awayTeam.name}</span>
                        <span class="score">${awayScore}</span>
                    </div>
                </div>
                <div class="match-status">
                    ${this.getStatusBadge(match.status)}
                </div>
            </div>
        `;
    }).join('');
}


    updateLastUpdated() {
        const lastUpdatedEl = document.getElementById('lastUpdated');
        if (lastUpdatedEl) {
            lastUpdatedEl.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        }
    }

    getMatchMinute(match) {
        if (match.status === 'IN_PLAY') {
            return match.minute ? `${match.minute}'` : '';
        }
        return this.formatMatchTime(match.utcDate);
    }

    getStatusBadge(status) {
        const statusMap = {
            'IN_PLAY': '<span class="badge bg-success">LIVE</span>',
            'PAUSED': '<span class="badge bg-warning">HT</span>',
            'FINISHED': '<span class="badge bg-secondary">FT</span>',
            'SCHEDULED': '<span class="badge bg-primary">Upcoming</span>'
        };
        return statusMap[status] || status;
    }

    formatMatchTime(utcDate) {
        return new Date(utcDate).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}