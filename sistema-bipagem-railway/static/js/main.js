// Sistema de Bipagem Master Hotelaria - JavaScript Principal
class BipageSistem {
    constructor() {
        this.barcodeInput = document.getElementById('barcodeInput');
        this.productSection = document.getElementById('productSection');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.successToast = document.getElementById('successToast');
        this.errorToast = document.getElementById('errorToast');
        this.todayCount = document.getElementById('todayCount');
        this.lastScan = document.getElementById('lastScan');
        this.recentList = document.getElementById('recentList');
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadTodayStats();
        this.loadRecentScans();
        this.focusInput();
        
        // Auto-focus no input a cada 5 segundos
        setInterval(() => this.focusInput(), 5000);
    }

    setupEventListeners() {
        // Input de código de barras
        this.barcodeInput.addEventListener('input', (e) => {
            const barcode = e.target.value.trim();
            if (barcode.length >= 8) { // Mínimo para código válido
                this.processBarcode(barcode);
            }
        });

        // Prevenir perda de foco
        this.barcodeInput.addEventListener('blur', () => {
            setTimeout(() => this.focusInput(), 100);
        });

        // Botões de ação
        document.getElementById('confirmBtn')?.addEventListener('click', () => {
            this.confirmScan();
        });

        document.getElementById('clearBtn')?.addEventListener('click', () => {
            this.clearScan();
        });

        document.getElementById('refreshBtn')?.addEventListener('click', () => {
            this.loadRecentScans();
        });

        // Teclas de atalho
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.clearScan();
            } else if (e.key === 'Enter' && this.productSection.style.display !== 'none') {
                this.confirmScan();
            }
        });
    }

    focusInput() {
        if (this.barcodeInput) {
            this.barcodeInput.focus();
        }
    }

    async processBarcode(barcode) {
        try {
            this.showLoading(true);
            this.updateScannerStatus('Processando código...', 'processing');
            
            const response = await fetch('/api/barcode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ barcode: barcode })
            });

            const data = await response.json();

            if (data.success) {
                this.displayProduct(data);
                this.showToast('success', 'Código processado com sucesso!');
                this.updateScannerStatus('Código processado', 'success');
            } else {
                throw new Error(data.error || 'Erro ao processar código');
            }

        } catch (error) {
            console.error('Erro ao processar código:', error);
            this.showToast('error', error.message || 'Erro ao processar código de barras');
            this.updateScannerStatus('Erro no processamento', 'error');
            this.clearInput();
        } finally {
            this.showLoading(false);
        }
    }

    displayProduct(data) {
        // Atualizar informações do produto
        document.getElementById('productName').textContent = data.produto.nome;
        document.getElementById('productSku').textContent = data.produto.sku;
        document.getElementById('productPrice').textContent = data.produto.preco;
        document.getElementById('productPlatform').textContent = this.getPlatformName(data.platform);
        document.getElementById('scanTime').textContent = new Date().toLocaleTimeString('pt-BR');
        
        // Atualizar imagem
        const productImage = document.getElementById('productImage');
        productImage.src = data.produto.imagem;
        productImage.onerror = () => {
            productImage.src = '/static/images/placeholder.jpg';
        };
        
        // Atualizar badge da plataforma
        const platformBadge = document.getElementById('platformBadge');
        platformBadge.textContent = this.getPlatformName(data.platform);
        platformBadge.className = `platform-badge ${data.platform}`;
        
        // Mostrar seção do produto
        this.productSection.style.display = 'block';
        this.productSection.scrollIntoView({ behavior: 'smooth' });
        
        // Salvar dados para confirmação
        this.currentScanData = data;
    }

    confirmScan() {
        if (this.currentScanData) {
            this.showToast('success', 'Bipagem confirmada com sucesso!');
            this.updateStats();
            this.loadRecentScans();
            this.clearScan();
        }
    }

    clearScan() {
        this.productSection.style.display = 'none';
        this.clearInput();
        this.updateScannerStatus('Pronto para leitura', 'ready');
        this.currentScanData = null;
    }

    clearInput() {
        this.barcodeInput.value = '';
        this.focusInput();
    }

    updateScannerStatus(message, type) {
        const scannerStatus = document.getElementById('scannerStatus');
        const pulseDot = scannerStatus.querySelector('.pulse-dot');
        
        scannerStatus.innerHTML = `<span class="pulse-dot"></span>${message}`;
        
        // Atualizar cor baseada no tipo
        const newPulseDot = scannerStatus.querySelector('.pulse-dot');
        switch (type) {
            case 'ready':
                newPulseDot.style.background = '#28a745';
                break;
            case 'processing':
                newPulseDot.style.background = '#ffc107';
                break;
            case 'success':
                newPulseDot.style.background = '#28a745';
                break;
            case 'error':
                newPulseDot.style.background = '#dc3545';
                break;
        }
    }

    showLoading(show) {
        if (show) {
            this.loadingOverlay.classList.add('show');
        } else {
            this.loadingOverlay.classList.remove('show');
        }
    }

    showToast(type, message) {
        const toast = type === 'success' ? this.successToast : this.errorToast;
        
        if (type === 'error') {
            document.getElementById('errorMessage').textContent = message;
        }
        
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }

    async loadTodayStats() {
        try {
            const today = new Date().toISOString().split('T')[0];
            const response = await fetch(`/api/reports/daily?date=${today}`);
            const data = await response.json();
            
            this.todayCount.textContent = data.total_geral || 0;
            
        } catch (error) {
            console.error('Erro ao carregar estatísticas:', error);
        }
    }

    async loadRecentScans() {
        try {
            const today = new Date().toISOString().split('T')[0];
            const response = await fetch(`/api/reports/daily?date=${today}`);
            const data = await response.json();
            
            // Por enquanto, mostrar dados simulados
            this.displayRecentScans([]);
            
        } catch (error) {
            console.error('Erro ao carregar bipagens recentes:', error);
            this.displayRecentScans([]);
        }
    }

    displayRecentScans(scans) {
        if (scans.length === 0) {
            this.recentList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📦</div>
                    <p>Nenhuma bipagem realizada hoje</p>
                </div>
            `;
            return;
        }

        const html = scans.map(scan => `
            <div class="recent-item">
                <div class="recent-icon">${this.getPlatformIcon(scan.platform)}</div>
                <div class="recent-details">
                    <h5>${scan.produto.nome}</h5>
                    <p>SKU: ${scan.produto.sku} • ${this.getPlatformName(scan.platform)}</p>
                </div>
                <div class="recent-time">${scan.hora}</div>
            </div>
        `).join('');

        this.recentList.innerHTML = html;
    }

    updateStats() {
        // Atualizar contador do dia
        const currentCount = parseInt(this.todayCount.textContent) || 0;
        this.todayCount.textContent = currentCount + 1;
        
        // Atualizar última bipagem
        this.lastScan.textContent = new Date().toLocaleTimeString('pt-BR');
    }

    getPlatformName(platform) {
        const names = {
            'mercadolivre': 'Mercado Livre',
            'shopee': 'Shopee',
            'loja_integrada': 'Loja Integrada',
            'desconhecido': 'Desconhecido'
        };
        return names[platform] || platform;
    }

    getPlatformIcon(platform) {
        const icons = {
            'mercadolivre': 'ML',
            'shopee': 'SH',
            'loja_integrada': 'LI',
            'desconhecido': '?'
        };
        return icons[platform] || '?';
    }
}

// Inicializar sistema quando página carregar
document.addEventListener('DOMContentLoaded', () => {
    window.bipageSystem = new BipageSistem();
    
    // Log de inicialização
    console.log('🚀 Sistema de Bipagem Master Hotelaria iniciado');
    console.log('📱 Versão: 3.0');
    console.log('🔧 Status: Pronto para uso');
});

// Prevenir refresh acidental
window.addEventListener('beforeunload', (e) => {
    if (window.bipageSystem && window.bipageSystem.currentScanData) {
        e.preventDefault();
        e.returnValue = 'Você tem uma bipagem em andamento. Tem certeza que deseja sair?';
    }
});

// Service Worker para funcionamento offline (opcional)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/static/sw.js')
            .then(registration => {
                console.log('SW registrado com sucesso:', registration);
            })
            .catch(registrationError => {
                console.log('Falha ao registrar SW:', registrationError);
            });
    });
}

