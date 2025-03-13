// Basic JavaScript for ePOS Proxy Web Interface
document.addEventListener('DOMContentLoaded', () => {
    // Access global config values
    const domainSuffix = window.appConfig?.domainSuffix || 'epos';
    const proxyHostname = window.appConfig?.proxyHostname || 'proxy';
    
    // Initialize application
    initApp();
    
    // Set current year in footer
    const yearElements = document.querySelectorAll('.current-year');
    const currentYear = new Date().getFullYear();
    yearElements.forEach(el => el.textContent = currentYear);
    
    // Simple routing for the SPA
    function initApp() {
        const path = window.location.pathname;
        const contentDiv = document.getElementById('spa-content');
        
        if (!contentDiv) return;
        
        // Clear loading message
        contentDiv.innerHTML = '';
        
        // Create page content based on route
        if (path === '/web/dashboard' || path === '/web/') {
            renderDashboard(contentDiv);
        } else if (path.startsWith('/web/printers')) {
            renderPrintersList(contentDiv);
        } else if (path.startsWith('/web/print-jobs')) {
            renderPrintJobs(contentDiv);
        } else if (path.startsWith('/web/email-templates')) {
            renderEmailTemplates(contentDiv);
        } else if (path.startsWith('/web/settings')) {
            renderSettings(contentDiv);
        } else {
            // Default to dashboard
            renderDashboard(contentDiv);
        }
    }
    
    // Render dashboard
    function renderDashboard(container) {
        container.innerHTML = `
            <h2>Dashboard</h2>
            <div class="dashboard-wrapper">
                <div class="dashboard-card">
                    <h3>Server Status</h3>
                    <p>The ePOS Proxy Server is running.</p>
                    <p>Hostname: ${proxyHostname}.${domainSuffix}</p>
                    <p>Access your server at: <a href="https://${proxyHostname}.${domainSuffix}/">https://${proxyHostname}.${domainSuffix}/</a></p>
                </div>
                <div class="dashboard-card">
                    <h3>Recent Print Jobs</h3>
                    <p>Loading recent jobs...</p>
                </div>
                <div class="dashboard-card">
                    <h3>Configured Printers</h3>
                    <p>Loading printers...</p>
                </div>
            </div>
        `;
        
        // Fetch recent print jobs
        fetchRecentPrintJobs(container.querySelector('.dashboard-card:nth-child(2)'));
        
        // Fetch configured printers
        fetchConfiguredPrinters(container.querySelector('.dashboard-card:nth-child(3)'));
    }
    
    // Render printers list
    function renderPrintersList(container) {
        container.innerHTML = `
            <h2>Configured Printers</h2>
            <div class="printers-wrapper">
                <p>Loading printers...</p>
            </div>
        `;
        
        // Fetch and display printers
        fetchConfiguredPrinters(container.querySelector('.printers-wrapper'));
    }
    
    // Render print jobs
    function renderPrintJobs(container) {
        container.innerHTML = `
            <h2>Print Jobs</h2>
            <div class="print-jobs-wrapper">
                <p>Loading print jobs...</p>
            </div>
        `;
        
        // Fetch and display print jobs
        fetchPrintJobs(container.querySelector('.print-jobs-wrapper'));
    }
    
    // Render email templates
    function renderEmailTemplates(container) {
        container.innerHTML = `
            <h2>Email Templates</h2>
            <div class="templates-wrapper">
                <p>Loading email templates...</p>
            </div>
        `;
        
        // Fetch and display email templates (to be implemented)
        container.querySelector('.templates-wrapper').innerHTML = `
            <p>Email template management will be available soon.</p>
        `;
    }
    
    // Render settings
    function renderSettings(container) {
        container.innerHTML = `
            <h2>Server Settings</h2>
            <div class="settings-wrapper">
                <div class="settings-card">
                    <h3>DNS Server</h3>
                    <p>Loading DNS status...</p>
                </div>
                <div class="settings-card">
                    <h3>Configuration</h3>
                    <p>Loading configuration status...</p>
                </div>
            </div>
        `;
        
        // Fetch DNS status
        fetchDnsStatus(container.querySelector('.settings-card:nth-child(1)'));
        
        // Fetch configuration status
        fetchConfigStatus(container.querySelector('.settings-card:nth-child(2)'));
    }
    
    // API fetch functions
    async function fetchRecentPrintJobs(container) {
        try {
            const response = await fetch('/api/print_jobs?limit=5');
            if (!response.ok) {
                throw new Error('Failed to fetch print jobs');
            }
            
            const data = await response.json();
            
            if (data.jobs && data.jobs.length > 0) {
                let html = '<ul class="jobs-list">';
                data.jobs.forEach(job => {
                    html += `
                        <li>
                            <span class="job-id">${job.job_id.substring(0, 8)}</span>
                            <span class="job-printer">${job.printer_name}</span>
                            <span class="job-time">${new Date(job.created_at).toLocaleString()}</span>
                            <span class="job-status ${job.status}">${job.status}</span>
                        </li>
                    `;
                });
                html += '</ul>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<p>No recent print jobs found.</p>';
            }
        } catch (error) {
            console.error('Error fetching print jobs:', error);
            container.innerHTML = `<p>Error loading print jobs: ${error.message}</p>`;
        }
    }
    
    async function fetchConfiguredPrinters(container) {
        try {
            const response = await fetch('/printers');
            if (!response.ok) {
                throw new Error('Failed to fetch printers');
            }
            
            const data = await response.json();
            
            if (data.printers && Object.keys(data.printers).length > 0) {
                let html = '<ul class="printers-list">';
                for (const [name, info] of Object.entries(data.printers)) {
                    html += `
                        <li>
                            <span class="printer-name">${name}</span>
                            <span class="printer-url">${info.url}</span>
                            <span class="printer-dns">${info.dns_name}</span>
                        </li>
                    `;
                }
                html += '</ul>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<p>No printers configured.</p>';
            }
        } catch (error) {
            console.error('Error fetching printers:', error);
            container.innerHTML = `<p>Error loading printers: ${error.message}</p>`;
        }
    }
    
    async function fetchPrintJobs(container) {
        try {
            const response = await fetch('/api/print_jobs');
            if (!response.ok) {
                throw new Error('Failed to fetch print jobs');
            }
            
            const data = await response.json();
            
            if (data.jobs && data.jobs.length > 0) {
                let html = '<table class="jobs-table">';
                html += `
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Printer</th>
                            <th>Date</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                `;
                
                data.jobs.forEach(job => {
                    html += `
                        <tr>
                            <td>${job.job_id.substring(0, 8)}</td>
                            <td>${job.printer_name}</td>
                            <td>${new Date(job.created_at).toLocaleString()}</td>
                            <td class="${job.status}">${job.status}</td>
                        </tr>
                    `;
                });
                
                html += '</tbody></table>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<p>No print jobs found.</p>';
            }
        } catch (error) {
            console.error('Error fetching print jobs:', error);
            container.innerHTML = `<p>Error loading print jobs: ${error.message}</p>`;
        }
    }
    
    async function fetchDnsStatus(container) {
        try {
            const response = await fetch('/dns');
            if (!response.ok) {
                throw new Error('Failed to fetch DNS status');
            }
            
            const data = await response.json();
            
            let html = '';
            if (data.status === 'enabled') {
                html = `
                    <p>DNS Server: <span class="status-enabled">Enabled</span></p>
                    <p>Running: <span class="${data.running ? 'status-enabled' : 'status-disabled'}">${data.running ? 'Yes' : 'No'}</span></p>
                    <p>Port: ${data.port}</p>
                    <p>Hosts: ${data.hosts}</p>
                    <p>Domain Suffix: ${data.domain_suffix}</p>
                    <p>Proxy Hostname: ${data.proxy_hostname}</p>
                `;
            } else {
                html = '<p>DNS Server: <span class="status-disabled">Disabled</span></p>';
            }
            
            container.innerHTML = html;
        } catch (error) {
            console.error('Error fetching DNS status:', error);
            container.innerHTML = `<p>Error loading DNS status: ${error.message}</p>`;
        }
    }
    
    async function fetchConfigStatus(container) {
        try {
            const response = await fetch('/config');
            if (!response.ok) {
                throw new Error('Failed to fetch configuration status');
            }
            
            const data = await response.json();
            
            const html = `
                <p>Config Watching: <span class="${data.config_watching ? 'status-enabled' : 'status-disabled'}">${data.config_watching ? 'Enabled' : 'Disabled'}</span></p>
                <p>Printers File: ${data.printers_file}</p>
                <p>Printer Count: ${data.printer_count}</p>
            `;
            
            container.innerHTML = html;
        } catch (error) {
            console.error('Error fetching configuration status:', error);
            container.innerHTML = `<p>Error loading configuration status: ${error.message}</p>`;
        }
    }
}); 