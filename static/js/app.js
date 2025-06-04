/**
 * YouTube Shorts Niche Analyzer - Frontend JavaScript
 * Handles real-time updates, interactive features, and data visualizations
 */

class YouTubeAnalyzer {
    constructor() {
        this.charts = {};
        this.pollInterval = null;
        this.init();
    }

    init() {
        this.initializeEventListeners();
        this.initializeTooltips();
        this.initializeCharts();
        this.handleAnalysisStatus();
    }

    /**
     * Initialize all event listeners
     */
    initializeEventListeners() {
        // Keyword selection for analysis form
        this.handleKeywordSelection();
        
        // Form validation and submission
        this.handleFormSubmission();
        
        // Dynamic threshold display
        this.handleThresholdSlider();
        
        // Export functionality
        this.handleExportActions();
        
        // Session management
        this.handleSessionActions();
        
        // Real-time search suggestions
        this.handleSearchInput();
    }

    /**
     * Handle keyword button selection
     */
    handleKeywordSelection() {
        const keywordButtons = document.querySelectorAll('.keyword-btn');
        const searchInput = document.getElementById('search_query');
        
        if (keywordButtons.length > 0 && searchInput) {
            keywordButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    
                    // Update input value
                    const keyword = btn.dataset.keyword;
                    searchInput.value = keyword;
                    
                    // Visual feedback
                    keywordButtons.forEach(b => {
                        b.classList.remove('active', 'btn-primary');
                        b.classList.add('btn-outline-secondary');
                    });
                    
                    btn.classList.remove('btn-outline-secondary');
                    btn.classList.add('btn-primary', 'active');
                    
                    // Add animation
                    btn.style.transform = 'scale(0.95)';
                    setTimeout(() => {
                        btn.style.transform = 'scale(1)';
                    }, 150);
                });
            });
        }
    }

    /**
     * Handle form submission with validation
     */
    handleFormSubmission() {
        const analysisForm = document.getElementById('analysisForm');
        const submitBtn = document.getElementById('startAnalysisBtn');
        
        if (analysisForm && submitBtn) {
            analysisForm.addEventListener('submit', (e) => {
                // Validate form before submission
                if (!this.validateAnalysisForm()) {
                    e.preventDefault();
                    return;
                }
                
                // Update button state
                const originalHTML = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting Analysis...';
                submitBtn.disabled = true;
                
                // Add loading class to form
                analysisForm.classList.add('loading');
                
                // Prevent double submission
                setTimeout(() => {
                    if (submitBtn.disabled) {
                        submitBtn.innerHTML = originalHTML;
                        submitBtn.disabled = false;
                        analysisForm.classList.remove('loading');
                    }
                }, 30000); // 30 second timeout
            });
        }
    }

    /**
     * Validate analysis form inputs
     */
    validateAnalysisForm() {
        const errors = [];
        
        // Session name validation
        const sessionName = document.getElementById('session_name');
        if (sessionName && (!sessionName.value || sessionName.value.trim().length < 3)) {
            errors.push('Session name must be at least 3 characters long');
            this.highlightError(sessionName);
        }
        
        // Numeric field validation
        const numericFields = [
            { id: 'min_views_per_day', min: 1000, name: 'Minimum Views per Day' },
            { id: 'max_duration_seconds', min: 1, max: 300, name: 'Max Duration' },
            { id: 'max_channel_videos', min: 1, max: 100, name: 'Max Channel Videos' }
        ];
        
        numericFields.forEach(field => {
            const element = document.getElementById(field.id);
            if (element) {
                const value = parseInt(element.value);
                if (isNaN(value) || value < field.min || (field.max && value > field.max)) {
                    errors.push(`${field.name} must be between ${field.min} and ${field.max || 'unlimited'}`);
                    this.highlightError(element);
                }
            }
        });
        
        // Display errors if any
        if (errors.length > 0) {
            this.showFormErrors(errors);
            return false;
        }
        
        return true;
    }

    /**
     * Highlight form field with error
     */
    highlightError(element) {
        element.classList.add('is-invalid');
        setTimeout(() => {
            element.classList.remove('is-invalid');
        }, 3000);
    }

    /**
     * Show form validation errors
     */
    showFormErrors(errors) {
        // Remove existing error alerts
        const existingAlerts = document.querySelectorAll('.alert-danger.form-errors');
        existingAlerts.forEach(alert => alert.remove());
        
        // Create error alert
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show form-errors';
        alertDiv.innerHTML = `
            <h6><i class="fas fa-exclamation-triangle me-2"></i>Please fix the following errors:</h6>
            <ul class="mb-0">
                ${errors.map(error => `<li>${error}</li>`).join('')}
            </ul>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert at top of form
        const form = document.getElementById('analysisForm');
        if (form) {
            form.insertBefore(alertDiv, form.firstChild);
            alertDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    /**
     * Handle threshold slider with live updates
     */
    handleThresholdSlider() {
        const thresholdSlider = document.getElementById('face_detection_threshold');
        
        if (thresholdSlider) {
            // Create display element if it doesn't exist
            let display = thresholdSlider.parentElement.querySelector('.threshold-display');
            if (!display) {
                display = document.createElement('div');
                display.className = 'threshold-display text-center mt-2 fw-bold text-primary';
                thresholdSlider.parentElement.appendChild(display);
            }
            
            const updateDisplay = () => {
                const value = parseFloat(thresholdSlider.value);
                display.textContent = `Current: ${value.toFixed(1)} (${this.getThresholdLabel(value)})`;
            };
            
            thresholdSlider.addEventListener('input', updateDisplay);
            updateDisplay(); // Initial display
        }
    }

    /**
     * Get threshold sensitivity label
     */
    getThresholdLabel(value) {
        if (value <= 0.3) return 'Very Low Sensitivity';
        if (value <= 0.5) return 'Low Sensitivity';
        if (value <= 0.7) return 'Medium Sensitivity';
        if (value <= 0.9) return 'High Sensitivity';
        return 'Very High Sensitivity';
    }

    /**
     * Handle real-time search input suggestions
     */
    handleSearchInput() {
        const searchInput = document.getElementById('search_query');
        
        if (searchInput) {
            // Add debounced input handler for suggestions
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.updateSearchSuggestions(e.target.value);
                }, 300);
            });
        }
    }

    /**
     * Update search suggestions based on input
     */
    updateSearchSuggestions(query) {
        if (!query || query.length < 2) return;
        
        // Simple client-side filtering of popular keywords
        const keywordButtons = document.querySelectorAll('.keyword-btn');
        keywordButtons.forEach(btn => {
            const keyword = btn.dataset.keyword.toLowerCase();
            const matches = keyword.includes(query.toLowerCase());
            
            if (matches) {
                btn.style.opacity = '1';
                btn.style.transform = 'scale(1.05)';
            } else {
                btn.style.opacity = '0.6';
                btn.style.transform = 'scale(1)';
            }
        });
    }

    /**
     * Initialize Bootstrap tooltips
     */
    initializeTooltips() {
        // Initialize all tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
        
        // Add custom tooltips for metrics
        this.addMetricTooltips();
    }

    /**
     * Add custom tooltips for metric explanations
     */
    addMetricTooltips() {
        const metrics = {
            'viral-score': 'Composite score based on views/day, engagement, and channel metrics',
            'views-per-day': 'Average daily views since video publication',
            'engagement-ratio': 'Ratio of likes + comments to total views',
            'channel-age': 'Days since channel creation (newer = higher score)'
        };
        
        Object.entries(metrics).forEach(([className, tooltip]) => {
            const elements = document.querySelectorAll(`.${className}`);
            elements.forEach(el => {
                el.setAttribute('data-bs-toggle', 'tooltip');
                el.setAttribute('data-bs-placement', 'top');
                el.setAttribute('title', tooltip);
                new bootstrap.Tooltip(el);
            });
        });
    }

    /**
     * Initialize Chart.js visualizations
     */
    initializeCharts() {
        this.initializeNicheChart();
        this.initializeMetricsChart();
        this.initializeProgressChart();
    }

    /**
     * Initialize niche performance chart
     */
    initializeNicheChart() {
        const chartCanvas = document.getElementById('nicheChart');
        if (!chartCanvas) return;
        
        const ctx = chartCanvas.getContext('2d');
        
        // Extract data from the page
        const nicheData = this.extractNicheData();
        
        this.charts.niche = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: nicheData.labels,
                datasets: [{
                    label: 'Viral Score',
                    data: nicheData.scores,
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Top Niches by Viral Score'
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Viral Score'
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize metrics comparison chart
     */
    initializeMetricsChart() {
        const chartCanvas = document.getElementById('metricsChart');
        if (!chartCanvas) return;
        
        const ctx = chartCanvas.getContext('2d');
        const metricsData = this.extractMetricsData();
        
        this.charts.metrics = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Views/Day', 'Engagement', 'Viral Score', 'Channel Quality', 'Content Volume'],
                datasets: metricsData.datasets
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Niche Performance Comparison'
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }

    /**
     * Initialize analysis progress chart
     */
    initializeProgressChart() {
        const chartCanvas = document.getElementById('progressChart');
        if (!chartCanvas) return;
        
        const ctx = chartCanvas.getContext('2d');
        
        this.charts.progress = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Completed', 'Remaining'],
                datasets: [{
                    data: [0, 100],
                    backgroundColor: ['rgba(40, 167, 69, 0.8)', 'rgba(108, 117, 125, 0.3)'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Analysis Progress'
                    }
                }
            }
        });
    }

    /**
     * Extract niche data from DOM
     */
    extractNicheData() {
        const nicheCards = document.querySelectorAll('[data-niche-name]');
        const labels = [];
        const scores = [];
        
        nicheCards.forEach(card => {
            const name = card.dataset.nicheName;
            const scoreElement = card.querySelector('[data-viral-score]');
            const score = scoreElement ? parseFloat(scoreElement.dataset.viralScore) : 0;
            
            labels.push(name);
            scores.push(score);
        });
        
        return { labels, scores };
    }

    /**
     * Extract metrics data from DOM
     */
    extractMetricsData() {
        const datasets = [];
        const colors = [
            'rgba(255, 99, 132, 0.6)',
            'rgba(54, 162, 235, 0.6)',
            'rgba(255, 205, 86, 0.6)',
            'rgba(75, 192, 192, 0.6)',
            'rgba(153, 102, 255, 0.6)'
        ];
        
        const nicheCards = document.querySelectorAll('[data-niche-metrics]');
        
        nicheCards.forEach((card, index) => {
            if (index >= 5) return; // Limit to top 5 niches
            
            const metrics = JSON.parse(card.dataset.nicheMetrics || '{}');
            const name = card.dataset.nicheName || `Niche ${index + 1}`;
            
            datasets.push({
                label: name,
                data: [
                    this.normalizeMetric(metrics.viewsPerDay, 100000),
                    this.normalizeMetric(metrics.engagement, 0.1),
                    metrics.viralScore || 0,
                    this.normalizeMetric(metrics.channelQuality, 100),
                    this.normalizeMetric(metrics.contentVolume, 20)
                ],
                backgroundColor: colors[index],
                borderColor: colors[index].replace('0.6', '1'),
                borderWidth: 1
            });
        });
        
        return { datasets };
    }

    /**
     * Normalize metric to 0-100 scale
     */
    normalizeMetric(value, maxValue) {
        return Math.min(100, (value / maxValue) * 100);
    }

    /**
     * Handle analysis status polling and updates
     */
    handleAnalysisStatus() {
        const sessionId = this.getSessionIdFromURL();
        if (!sessionId) return;
        
        // Check if analysis is running
        const runningBadges = document.querySelectorAll('.badge');
        let hasRunningStatus = false;
        
        runningBadges.forEach(badge => {
            if (badge.textContent.includes('Running')) {
                hasRunningStatus = true;
            }
        });
        
        const progressBar = document.getElementById('progressBar');
        
        if (hasRunningStatus || progressBar) {
            this.startStatusPolling(sessionId);
        }
    }

    /**
     * Start polling for analysis status updates
     */
    startStatusPolling(sessionId) {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        this.pollInterval = setInterval(() => {
            this.updateAnalysisStatus(sessionId);
        }, 3000);
        
        // Initial update
        this.updateAnalysisStatus(sessionId);
    }

    /**
     * Update analysis status from server
     */
    async updateAnalysisStatus(sessionId) {
        try {
            const response = await fetch(`/api/analysis_status/${sessionId}`);
            const data = await response.json();
            
            // Update progress bar
            const progressBar = document.getElementById('progressBar');
            const progressText = document.getElementById('progressText');
            const statusText = document.getElementById('statusText');
            
            if (progressBar && progressText) {
                progressBar.style.width = `${data.progress}%`;
                progressBar.setAttribute('aria-valuenow', data.progress);
                progressText.textContent = `${data.progress}%`;
                
                // Update progress chart if exists
                if (this.charts.progress) {
                    this.charts.progress.data.datasets[0].data = [data.progress, 100 - data.progress];
                    this.charts.progress.update();
                }
            }
            
            if (statusText) {
                statusText.textContent = data.current_status || 'Processing...';
                this.animateStatusText(statusText);
            }
            
            // Update statistics
            this.updateAnalysisStats(data);
            
            // Check if completed
            if (data.status === 'completed' || data.status === 'failed') {
                this.handleAnalysisComplete(data.status);
            }
            
        } catch (error) {
            console.error('Error fetching analysis status:', error);
            this.handleStatusError();
        }
    }

    /**
     * Animate status text for visual feedback
     */
    animateStatusText(element) {
        element.style.opacity = '0.7';
        setTimeout(() => {
            element.style.opacity = '1';
        }, 200);
    }

    /**
     * Update analysis statistics in real-time
     */
    updateAnalysisStats(data) {
        const statsElements = {
            'total_videos_analyzed': data.total_videos_analyzed,
            'total_channels_found': data.total_channels_found,
            'total_niches_identified': data.total_niches_identified
        };
        
        Object.entries(statsElements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element && value !== undefined) {
                this.animateNumberUpdate(element, value);
            }
        });
    }

    /**
     * Animate number updates with counting effect
     */
    animateNumberUpdate(element, newValue) {
        const currentValue = parseInt(element.textContent) || 0;
        if (currentValue === newValue) return;
        
        const increment = newValue > currentValue ? 1 : -1;
        const duration = Math.min(1000, Math.abs(newValue - currentValue) * 50);
        const steps = Math.abs(newValue - currentValue);
        const stepDuration = duration / steps;
        
        let current = currentValue;
        const timer = setInterval(() => {
            current += increment;
            element.textContent = current.toLocaleString();
            
            if (current === newValue) {
                clearInterval(timer);
                element.classList.add('text-success');
                setTimeout(() => {
                    element.classList.remove('text-success');
                }, 1000);
            }
        }, stepDuration);
    }

    /**
     * Handle analysis completion
     */
    handleAnalysisComplete(status) {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        
        if (status === 'completed') {
            this.showSuccessMessage();
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else if (status === 'failed') {
            this.showErrorMessage();
        }
    }

    /**
     * Show success message for completed analysis
     */
    showSuccessMessage() {
        const message = this.createAlert('success', 'Analysis Completed!', 'Your niche analysis has finished successfully. Refreshing results...');
        this.showAlert(message);
    }

    /**
     * Show error message for failed analysis
     */
    showErrorMessage() {
        const message = this.createAlert('danger', 'Analysis Failed', 'There was an error during analysis. Please try again or check your API configuration.');
        this.showAlert(message);
    }

    /**
     * Handle status polling errors
     */
    handleStatusError() {
        console.warn('Status polling error - will retry...');
        // Don't show error to user for temporary network issues
    }

    /**
     * Create alert element
     */
    createAlert(type, title, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            <strong><i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>${title}</strong>
            <div>${message}</div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        return alertDiv;
    }

    /**
     * Show alert with auto-dismiss
     */
    showAlert(alertElement) {
        document.body.appendChild(alertElement);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.remove();
            }
        }, 5000);
    }

    /**
     * Handle export actions
     */
    handleExportActions() {
        const exportButton = document.querySelector('[href*="export_csv"]');
        
        if (exportButton) {
            exportButton.addEventListener('click', (e) => {
                // Add loading state to export button
                const originalText = exportButton.innerHTML;
                exportButton.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating CSV...';
                exportButton.classList.add('disabled');
                
                // Reset button after delay
                setTimeout(() => {
                    exportButton.innerHTML = originalText;
                    exportButton.classList.remove('disabled');
                }, 3000);
            });
        }
    }

    /**
     * Handle session management actions
     */
    handleSessionActions() {
        // Delete session confirmation
        const deleteButtons = document.querySelectorAll('[data-action="delete-session"]');
        
        deleteButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                
                const sessionName = btn.dataset.sessionName;
                if (confirm(`Are you sure you want to delete the session "${sessionName}"? This action cannot be undone.`)) {
                    // Submit the delete form
                    const form = btn.closest('form');
                    if (form) {
                        form.submit();
                    }
                }
            });
        });
    }

    /**
     * Get session ID from current URL
     */
    getSessionIdFromURL() {
        const path = window.location.pathname;
        const match = path.match(/\/results\/(\d+)/);
        return match ? match[1] : null;
    }

    /**
     * Utility function to format numbers
     */
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    /**
     * Utility function to format percentages
     */
    formatPercentage(decimal) {
        return (decimal * 100).toFixed(2) + '%';
    }

    /**
     * Add smooth scrolling to anchor links
     */
    initializeSmoothScrolling() {
        const anchorLinks = document.querySelectorAll('a[href^="#"]');
        
        anchorLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    /**
     * Initialize lazy loading for images
     */
    initializeLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });
            
            images.forEach(img => imageObserver.observe(img));
        } else {
            // Fallback for older browsers
            images.forEach(img => {
                img.src = img.dataset.src;
                img.classList.remove('lazy');
            });
        }
    }

    /**
     * Cleanup function
     */
    destroy() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        // Destroy charts
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.youtubeAnalyzer = new YouTubeAnalyzer();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.youtubeAnalyzer) {
        window.youtubeAnalyzer.destroy();
    }
});

// Additional utility functions for the application

/**
 * Copy text to clipboard with visual feedback
 */
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
        button.classList.add('btn-success');
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy text: ', err);
    });
}

/**
 * Format duration in seconds to human readable format
 */
function formatDuration(seconds) {
    if (seconds < 60) {
        return `${seconds}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}:${minutes.toString().padStart(2, '0')}:00`;
    }
}

/**
 * Debounce function for limiting function calls
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function for limiting function calls
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// Export for use in other scripts if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = YouTubeAnalyzer;
}
