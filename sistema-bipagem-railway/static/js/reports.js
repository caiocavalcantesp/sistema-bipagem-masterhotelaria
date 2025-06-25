// Sistema de Relatórios - JavaScript
class ReportsSystem {
    constructor() {
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.successToast = document.getElementById('successToast');
        this.errorToast = document.getElementById('errorToast');
        
        this.charts = {};
        this.currentData = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeDateFilters();
        this.loadInitialData();
    }

    setupEventListeners() {
        // Filter buttons
        document.getElementById('applyFiltersBtn')?.addEventListener('click', () => {
            this.applyFilters();
        });

        document.getElementById('resetFiltersBtn')?.addEventListener('click', () => {
            this.resetFilters();
        });

        // Export buttons
        document.getElementById('exportDailyBtn')?.addEventListener('click', () => {
            this.exportChart('daily');
        });

        document.getElementById('exportPlatformBtn')?.addEventListener('click', () => {
            this.exportChart('platform');
        });

        document.getElementById('exportHourlyBtn')?.addEventListener('click', () => {
            this.exportChart('hourly');
        });

        document.getElementById('exportTableBtn')?.addEventListener('click', () => {
            this.exportTableData();
        });
    }

    initializeDateFilters() {
        const today = new Date();
        const lastWeek = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
        
        document.getElementById('startDate').value = lastWeek.toISOString().split('T')[0];
        document.getElementById('endDate').value = today.toISOString().split('T')[0];
    }

    async loadInitialData() {
        this.showLoading(true);
        
        try {
            await this.loadReportData();
            this.updateSummaryCards();
            this.initializeCharts();
            this.updateDetailTable();
            this.generateInsights();
            
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            this.showError('Erro ao carregar dados do relatório');
        } finally {
            this.showLoading(false);
        }
    }

    async loadReportData() {
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        const platform = document.getElementById('platformFilter').value;
        
        try {
            const response = await fetch(`/api/reports/period?start_date=${startDate}&end_date=${endDate}&platform=${platform}`);
            const data = await response.json();
            
            // Simular dados para demonstração
            this.currentData = this.generateSampleData(startDate, endDate);
            
        } catch (error) {
            // Usar dados simulados em caso de erro
            this.currentData = this.generateSampleData(startDate, endDate);
        }
    }

    generateSampleData(startDate, endDate) {
        const start = new Date(startDate);
        const end = new Date(endDate);
        const days = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
        
        const data = {
            summary: {
                total: 0,
                average: 0,
                bestDay: { date: '', count: 0 },
                topPlatform: { name: 'Mercado Livre', percentage: 45 }
            },
            daily: [],
            platforms: {
                mercadolivre: 0,
                shopee: 0,
                loja_integrada: 0
            },
            hourly: Array(24).fill(0)
        };
        
        // Gerar dados simulados por dia
        for (let i = 0; i < days; i++) {
            const currentDate = new Date(start.getTime() + i * 24 * 60 * 60 * 1000);
            const dateStr = currentDate.toISOString().split('T')[0];
            
            // Simular bipagens (mais atividade em dias úteis)
            const isWeekend = currentDate.getDay() === 0 || currentDate.getDay() === 6;
            const baseBipagens = isWeekend ? Math.floor(Math.random() * 20) : Math.floor(Math.random() * 50) + 20;
            
            const dayData = {
                date: dateStr,
                mercadolivre: Math.floor(baseBipagens * 0.45),
                shopee: Math.floor(baseBipagens * 0.35),
                loja_integrada: Math.floor(baseBipagens * 0.20),
                total: baseBipagens
            };
            
            data.daily.push(dayData);
            data.summary.total += dayData.total;
            data.platforms.mercadolivre += dayData.mercadolivre;
            data.platforms.shopee += dayData.shopee;
            data.platforms.loja_integrada += dayData.loja_integrada;
            
            if (dayData.total > data.summary.bestDay.count) {
                data.summary.bestDay = { date: dateStr, count: dayData.total };
            }
        }
        
        data.summary.average = Math.round(data.summary.total / days);
        
        // Gerar dados por horário (simulado)
        for (let hour = 0; hour < 24; hour++) {
            if (hour >= 8 && hour <= 18) {
                data.hourly[hour] = Math.floor(Math.random() * 30) + 10;
            } else {
                data.hourly[hour] = Math.floor(Math.random() * 10);
            }
        }
        
        return data;
    }

    updateSummaryCards() {
        if (!this.currentData) return;
        
        const { summary } = this.currentData;
        
        document.getElementById('totalBipagens').textContent = summary.total.toLocaleString();
        document.getElementById('mediaDiaria').textContent = summary.average.toLocaleString();
        document.getElementById('melhorDia').textContent = summary.bestDay.count.toLocaleString();
        document.getElementById('melhorDiaData').textContent = this.formatDate(summary.bestDay.date);
        document.getElementById('plataformaLider').textContent = summary.topPlatform.name;
        document.getElementById('liderPercentual').textContent = `${summary.topPlatform.percentage}%`;
        
        // Simular mudanças percentuais
        document.getElementById('totalChange').textContent = '+12%';
        document.getElementById('totalChange').className = 'summary-change positive';
        
        document.getElementById('mediaChange').textContent = '+8%';
        document.getElementById('mediaChange').className = 'summary-change positive';
    }

    initializeCharts() {
        this.initializeDailyChart();
        this.initializePlatformChart();
        this.initializeHourlyChart();
    }

    initializeDailyChart() {
        const ctx = document.getElementById('dailyChart').getContext('2d');
        
        if (this.charts.daily) {
            this.charts.daily.destroy();
        }
        
        const labels = this.currentData.daily.map(d => this.formatDate(d.date));
        const data = this.currentData.daily.map(d => d.total);
        
        this.charts.daily = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Bipagens por Dia',
                    data: data,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#667eea',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    initializePlatformChart() {
        const ctx = document.getElementById('platformChart').getContext('2d');
        
        if (this.charts.platform) {
            this.charts.platform.destroy();
        }
        
        const { platforms } = this.currentData;
        
        this.charts.platform = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Mercado Livre', 'Shopee', 'Loja Integrada'],
                datasets: [{
                    data: [platforms.mercadolivre, platforms.shopee, platforms.loja_integrada],
                    backgroundColor: ['#FFE600', '#EE4D2D', '#2E7D32'],
                    borderWidth: 0,
                    hoverOffset: 10
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }

    initializeHourlyChart() {
        const ctx = document.getElementById('hourlyChart').getContext('2d');
        
        if (this.charts.hourly) {
            this.charts.hourly.destroy();
        }
        
        const labels = Array.from({length: 24}, (_, i) => `${i.toString().padStart(2, '0')}:00`);
        
        this.charts.hourly = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Bipagens por Hora',
                    data: this.currentData.hourly,
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: '#667eea',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    updateDetailTable() {
        const tbody = document.getElementById('detailTableBody');
        
        if (!this.currentData || this.currentData.daily.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="no-data">
                        <div class="empty-state">
                            <div class="empty-icon">📊</div>
                            <p>Nenhum dado encontrado para o período selecionado</p>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }
        
        const totalPeriod = this.currentData.summary.total;
        
        const rows = this.currentData.daily.map(day => {
            const percentage = totalPeriod > 0 ? ((day.total / totalPeriod) * 100).toFixed(1) : '0.0';
            
            return `
                <tr>
                    <td>${this.formatDate(day.date)}</td>
                    <td>${day.mercadolivre}</td>
                    <td>${day.shopee}</td>
                    <td>${day.loja_integrada}</td>
                    <td><strong>${day.total}</strong></td>
                    <td>${percentage}%</td>
                </tr>
            `;
        }).join('');
        
        tbody.innerHTML = rows;
    }

    generateInsights() {
        const insightsGrid = document.getElementById('insightsGrid');
        
        if (!this.currentData) return;
        
        const insights = this.analyzeData();
        
        const html = insights.map(insight => `
            <div class="insight-item">
                <div class="insight-icon">${insight.icon}</div>
                <div class="insight-content">
                    <h4>${insight.title}</h4>
                    <p>${insight.description}</p>
                </div>
            </div>
        `).join('');
        
        insightsGrid.innerHTML = html;
    }

    analyzeData() {
        if (!this.currentData) return [];
        
        const insights = [];
        
        // Análise de tendência
        const dailyData = this.currentData.daily;
        if (dailyData.length >= 2) {
            const firstHalf = dailyData.slice(0, Math.floor(dailyData.length / 2));
            const secondHalf = dailyData.slice(Math.floor(dailyData.length / 2));
            
            const firstAvg = firstHalf.reduce((sum, day) => sum + day.total, 0) / firstHalf.length;
            const secondAvg = secondHalf.reduce((sum, day) => sum + day.total, 0) / secondHalf.length;
            
            const trend = secondAvg > firstAvg ? 'crescimento' : 'declínio';
            const percentage = Math.abs(((secondAvg - firstAvg) / firstAvg) * 100).toFixed(1);
            
            insights.push({
                icon: trend === 'crescimento' ? '📈' : '📉',
                title: 'Tendência Geral',
                description: `${trend === 'crescimento' ? 'Crescimento' : 'Declínio'} de ${percentage}% na segunda metade do período em relação à primeira.`
            });
        }
        
        // Análise de horário de pico
        const peakHour = this.currentData.hourly.indexOf(Math.max(...this.currentData.hourly));
        insights.push({
            icon: '⏰',
            title: 'Horário de Pico',
            description: `Maior atividade registrada às ${peakHour.toString().padStart(2, '0')}:00, com ${this.currentData.hourly[peakHour]} bipagens em média.`
        });
        
        // Análise de plataforma dominante
        const platforms = this.currentData.platforms;
        const topPlatform = Object.keys(platforms).reduce((a, b) => platforms[a] > platforms[b] ? a : b);
        const topPlatformName = this.getPlatformDisplayName(topPlatform);
        const topPlatformPercentage = ((platforms[topPlatform] / this.currentData.summary.total) * 100).toFixed(1);
        
        insights.push({
            icon: '🏪',
            title: 'Plataforma Dominante',
            description: `${topPlatformName} representa ${topPlatformPercentage}% de todas as bipagens do período.`
        });
        
        return insights;
    }

    getPlatformDisplayName(platform) {
        const names = {
            'mercadolivre': 'Mercado Livre',
            'shopee': 'Shopee',
            'loja_integrada': 'Loja Integrada'
        };
        return names[platform] || platform;
    }

    async applyFilters() {
        this.showLoading(true);
        
        try {
            await this.loadReportData();
            this.updateSummaryCards();
            this.initializeCharts();
            this.updateDetailTable();
            this.generateInsights();
            
            this.showSuccess('Relatório atualizado com sucesso!');
            
        } catch (error) {
            this.showError('Erro ao aplicar filtros');
        } finally {
            this.showLoading(false);
        }
    }

    resetFilters() {
        this.initializeDateFilters();
        document.getElementById('platformFilter').value = 'all';
        this.applyFilters();
    }

    exportChart(chartType) {
        try {
            const chart = this.charts[chartType];
            if (!chart) {
                this.showError('Gráfico não encontrado');
                return;
            }
            
            const url = chart.toBase64Image();
            const link = document.createElement('a');
            link.download = `grafico-${chartType}-${new Date().toISOString().split('T')[0]}.png`;
            link.href = url;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.showSuccess('Gráfico exportado com sucesso!');
            
        } catch (error) {
            this.showError('Erro ao exportar gráfico');
        }
    }

    exportTableData() {
        try {
            if (!this.currentData || !this.currentData.daily.length) {
                this.showError('Nenhum dado para exportar');
                return;
            }
            
            const headers = ['Data', 'Mercado Livre', 'Shopee', 'Loja Integrada', 'Total', '% do Período'];
            const totalPeriod = this.currentData.summary.total;
            
            const csvContent = [
                headers.join(','),
                ...this.currentData.daily.map(day => {
                    const percentage = totalPeriod > 0 ? ((day.total / totalPeriod) * 100).toFixed(1) : '0.0';
                    return [
                        this.formatDate(day.date),
                        day.mercadolivre,
                        day.shopee,
                        day.loja_integrada,
                        day.total,
                        `${percentage}%`
                    ].join(',');
                })
            ].join('\n');
            
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            
            link.setAttribute('href', url);
            link.setAttribute('download', `relatorio-bipagem-${new Date().toISOString().split('T')[0]}.csv`);
            link.style.visibility = 'hidden';
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.showSuccess('Dados exportados com sucesso!');
            
        } catch (error) {
            this.showError('Erro ao exportar dados');
        }
    }

    formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString('pt-BR');
    }

    showLoading(show) {
        if (show) {
            this.loadingOverlay.classList.add('show');
        } else {
            this.loadingOverlay.classList.remove('show');
        }
    }

    showSuccess(message) {
        document.getElementById('successMessage').textContent = message;
        this.successToast.classList.add('show');
        
        setTimeout(() => {
            this.successToast.classList.remove('show');
        }, 3000);
    }

    showError(message) {
        document.getElementById('errorMessage').textContent = message;
        this.errorToast.classList.add('show');
        
        setTimeout(() => {
            this.errorToast.classList.remove('show');
        }, 3000);
    }
}

// Inicializar sistema de relatórios
document.addEventListener('DOMContentLoaded', () => {
    window.reportsSystem = new ReportsSystem();
    console.log('📊 Sistema de Relatórios iniciado');
});

