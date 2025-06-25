// Sistema de Configuração - JavaScript
class ConfigSystem {
    constructor() {
        this.platformsGrid = document.getElementById('platformsGrid');
        this.successToast = document.getElementById('successToast');
        this.errorToast = document.getElementById('errorToast');
        
        this.init();
    }

    init() {
        this.loadPlatforms();
        this.setupEventListeners();
        this.loadSystemStats();
        this.loadSettings();
    }

    setupEventListeners() {
        // Settings toggles
        document.getElementById('soundNotifications')?.addEventListener('change', (e) => {
            this.saveSetting('soundNotifications', e.target.checked);
        });

        document.getElementById('autoFocus')?.addEventListener('change', (e) => {
            this.saveSetting('autoFocus', e.target.checked);
        });

        document.getElementById('autoClear')?.addEventListener('change', (e) => {
            this.saveSetting('autoClear', e.target.checked);
        });

        document.getElementById('readTimeout')?.addEventListener('change', (e) => {
            this.saveSetting('readTimeout', e.target.value);
        });

        // Data management buttons
        document.getElementById('exportDataBtn')?.addEventListener('click', () => {
            this.exportData();
        });

        document.getElementById('backupDataBtn')?.addEventListener('click', () => {
            this.backupData();
        });

        document.getElementById('clearDataBtn')?.addEventListener('click', () => {
            this.clearData();
        });
    }

    async loadPlatforms() {
        try {
            const response = await fetch('/oauth/platforms');
            const platforms = await response.json();
            
            this.displayPlatforms(platforms);
            
        } catch (error) {
            console.error('Erro ao carregar plataformas:', error);
            this.showError('Erro ao carregar plataformas de integração');
        }
    }

    displayPlatforms(platforms) {
        const html = platforms.map(platform => `
            <div class="platform-card">
                <div class="platform-header">
                    <div class="platform-icon ${platform.id}">
                        ${this.getPlatformIcon(platform.id)}
                    </div>
                    <div class="platform-info">
                        <h4>${platform.name}</h4>
                        <div class="platform-status ${platform.status}">
                            ${platform.status === 'connected' ? '🟢' : '🔴'}
                            ${platform.status === 'connected' ? 'Conectado' : 'Desconectado'}
                        </div>
                    </div>
                </div>
                
                <div class="platform-description">
                    ${this.getPlatformDescription(platform.id)}
                </div>
                
                <div class="platform-actions">
                    ${platform.status === 'connected' ? `
                        <button class="connect-btn connected" disabled>
                            ✅ Conectado
                        </button>
                        <button class="disconnect-btn" onclick="configSystem.disconnectPlatform('${platform.id}')">
                            🔌
                        </button>
                    ` : `
                        <a href="${platform.authorize_url}" 
                           class="connect-btn disconnected" 
                           target="_blank"
                           onclick="configSystem.handleConnect('${platform.id}')">
                            🔗 Conectar Conta
                        </a>
                    `}
                </div>
            </div>
        `).join('');

        this.platformsGrid.innerHTML = html;
    }

    getPlatformIcon(platformId) {
        const icons = {
            'mercadolivre': 'ML',
            'shopee': 'SH',
            'loja_integrada': 'LI'
        };
        return icons[platformId] || '?';
    }

    getPlatformDescription(platformId) {
        const descriptions = {
            'mercadolivre': 'Conecte sua conta do Mercado Livre para buscar automaticamente informações de produtos, preços e imagens dos seus anúncios.',
            'shopee': 'Integre com a Shopee para acessar dados dos seus produtos, incluindo SKUs, preços e imagens de forma automática.',
            'loja_integrada': 'Conecte sua Loja Integrada para sincronizar informações de produtos e facilitar o processo de bipagem.'
        };
        return descriptions[platformId] || 'Conecte esta plataforma para integração automática.';
    }

    handleConnect(platformId) {
        this.showSuccess(`Abrindo página de autorização para ${this.getPlatformName(platformId)}`);
        
        // Verificar status após 5 segundos
        setTimeout(() => {
            this.loadPlatforms();
        }, 5000);
    }

    async disconnectPlatform(platformId) {
        if (confirm(`Tem certeza que deseja desconectar ${this.getPlatformName(platformId)}?`)) {
            try {
                // Aqui seria feita a chamada para desconectar
                // Por enquanto, simular desconexão
                this.showSuccess(`${this.getPlatformName(platformId)} desconectado com sucesso`);
                this.loadPlatforms();
                
            } catch (error) {
                this.showError('Erro ao desconectar plataforma');
            }
        }
    }

    getPlatformName(platformId) {
        const names = {
            'mercadolivre': 'Mercado Livre',
            'shopee': 'Shopee',
            'loja_integrada': 'Loja Integrada'
        };
        return names[platformId] || platformId;
    }

    async loadSystemStats() {
        try {
            // Simular carregamento de estatísticas
            // Em produção, seria uma chamada real para a API
            document.getElementById('totalBipagens').textContent = '0';
            document.getElementById('totalDias').textContent = '0';
            document.getElementById('mediaDay').textContent = '0';
            
        } catch (error) {
            console.error('Erro ao carregar estatísticas:', error);
        }
    }

    loadSettings() {
        // Carregar configurações salvas do localStorage
        const settings = this.getStoredSettings();
        
        document.getElementById('soundNotifications').checked = settings.soundNotifications;
        document.getElementById('autoFocus').checked = settings.autoFocus;
        document.getElementById('autoClear').checked = settings.autoClear;
        document.getElementById('readTimeout').value = settings.readTimeout;
    }

    getStoredSettings() {
        const defaults = {
            soundNotifications: true,
            autoFocus: true,
            autoClear: true,
            readTimeout: '2000'
        };

        try {
            const stored = localStorage.getItem('bipageSettings');
            return stored ? { ...defaults, ...JSON.parse(stored) } : defaults;
        } catch {
            return defaults;
        }
    }

    saveSetting(key, value) {
        try {
            const settings = this.getStoredSettings();
            settings[key] = value;
            localStorage.setItem('bipageSettings', JSON.stringify(settings));
            
            this.showSuccess('Configuração salva com sucesso');
            
        } catch (error) {
            this.showError('Erro ao salvar configuração');
        }
    }

    async exportData() {
        try {
            this.showSuccess('Preparando exportação de dados...');
            
            // Simular exportação
            setTimeout(() => {
                const data = {
                    exportDate: new Date().toISOString(),
                    totalBipagens: 0,
                    bipagens: []
                };
                
                const blob = new Blob([JSON.stringify(data, null, 2)], {
                    type: 'application/json'
                });
                
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `bipagem-export-${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                this.showSuccess('Dados exportados com sucesso');
            }, 1000);
            
        } catch (error) {
            this.showError('Erro ao exportar dados');
        }
    }

    async backupData() {
        try {
            this.showSuccess('Criando backup dos dados...');
            
            // Simular backup
            setTimeout(() => {
                this.showSuccess('Backup criado com sucesso');
            }, 2000);
            
        } catch (error) {
            this.showError('Erro ao criar backup');
        }
    }

    async clearData() {
        if (confirm('⚠️ ATENÇÃO: Esta ação irá apagar TODOS os dados de bipagem. Esta ação não pode ser desfeita. Tem certeza?')) {
            if (confirm('Confirme novamente: Deseja realmente apagar todos os dados?')) {
                try {
                    this.showSuccess('Limpando dados do sistema...');
                    
                    // Simular limpeza
                    setTimeout(() => {
                        this.loadSystemStats();
                        this.showSuccess('Todos os dados foram removidos');
                    }, 2000);
                    
                } catch (error) {
                    this.showError('Erro ao limpar dados');
                }
            }
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

// Inicializar sistema de configuração
document.addEventListener('DOMContentLoaded', () => {
    window.configSystem = new ConfigSystem();
    console.log('🔧 Sistema de Configuração iniciado');
});

// Verificar conexões OAuth periodicamente
setInterval(() => {
    if (window.configSystem) {
        window.configSystem.loadPlatforms();
    }
}, 30000); // A cada 30 segundos

