/**
 * JavSP WebUI - 简化版本
 */

class JavSPWebUI {
    constructor() {
        this.currentPath = '/tmp/gui_demo';
        this.scanResults = [];
        this.isScanning = false;

        this.init();
    }

    init() {
        console.log('JavSP WebUI 启动中...');

        // 绑定事件
        this.bindEvents();

        // 加载初始数据
        this.loadFileBrowser();
        this.loadScanResults();

        console.log('JavSP WebUI 启动完成');
    }

    bindEvents() {
        // 开始扫描按钮
        document.getElementById('start-scan-btn').addEventListener('click', () => {
            this.startScan();
        });

        // 刷新文件按钮
        document.getElementById('refresh-files-btn').addEventListener('click', () => {
            this.loadFileBrowser();
        });

        // 清空结果按钮
        document.getElementById('clear-results-btn').addEventListener('click', () => {
            this.clearResults();
        });

        // 扫描路径输入框回车事件
        document.getElementById('scan-path').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.currentPath = e.target.value;
                this.loadFileBrowser();
            }
        });
    }

    // 显示/隐藏进度遮罩
    showProgress(show = true, text = '处理中...') {
        const overlay = document.getElementById('progress-overlay');
        const textElement = document.getElementById('progress-text');

        if (show) {
            textElement.textContent = text;
            overlay.style.display = 'block';
        } else {
            overlay.style.display = 'none';
        }
    }

    // 显示消息
    showMessage(message, type = 'info') {
        // 简单的消息显示，可以后续改进
        console.log(`[${type}] ${message}`);

        // 也可以在界面上显示
        const statusDiv = document.getElementById('scan-status');
        const statusText = document.getElementById('status-text');

        if (type === 'error') {
            statusDiv.className = 'mt-3';
            statusDiv.innerHTML = `<div class="alert alert-danger">${message}</div>`;
            statusDiv.style.display = 'block';
        } else {
            statusText.textContent = message;
            statusDiv.style.display = 'block';
        }

        // 3秒后自动隐藏
        setTimeout(() => {
            if (!this.isScanning) {
                statusDiv.style.display = 'none';
            }
        }, 3000);
    }

    // 加载文件浏览器
    async loadFileBrowser(path = null) {
        if (path) {
            this.currentPath = path;
        }

        try {
            const response = await fetch(`/api/files/browse?path=${encodeURIComponent(this.currentPath)}`);
            const data = await response.json();

            if (response.ok) {
                this.displayFileBrowser(data);
                // 更新路径输入框
                document.getElementById('scan-path').value = this.currentPath;
            } else {
                this.showMessage(`加载文件失败: ${data.error || '未知错误'}`, 'error');
            }
        } catch (error) {
            console.error('加载文件浏览器失败:', error);
            this.showMessage('加载文件浏览器失败', 'error');
        }
    }

    // 显示文件浏览器
    displayFileBrowser(data) {
        const browser = document.getElementById('file-browser');
        let html = '';

        // 父目录
        if (data.parent_path) {
            html += `
                <div class="file-item" onclick="app.loadFileBrowser('${data.parent_path}')">
                    <i class="fas fa-level-up-alt me-2"></i>
                    <span>上级目录</span>
                </div>
            `;
        }

        // 目录和文件
        data.items.forEach(item => {
            const icon = item.type === 'directory'
                ? 'fas fa-folder'
                : item.is_video ? 'fas fa-film' : 'fas fa-file';

            const clickAction = item.type === 'directory'
                ? `onclick="app.loadFileBrowser('${item.path}')"`
                : '';

            html += `
                <div class="file-item" ${clickAction}>
                    <i class="${icon} me-2"></i>
                    <span>${this.escapeHtml(item.name)}</span>
                    ${item.size ? `<small class="text-muted ms-2">${item.size}</small>` : ''}
                </div>
            `;
        });

        browser.innerHTML = html || '<div class="text-center text-muted py-4">空目录</div>';
    }

    // 开始扫描
    async startScan() {
        if (this.isScanning) {
            this.showMessage('正在扫描中，请等待', 'warning');
            return;
        }

        const path = document.getElementById('scan-path').value.trim();
        if (!path) {
            this.showMessage('请输入扫描路径', 'warning');
            return;
        }

        const forceRescan = document.getElementById('force-rescan').checked;

        this.isScanning = true;
        this.showProgress(true, '启动扫描...');

        try {
            const response = await fetch('/api/scan/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    path: path,
                    force_rescan: forceRescan
                })
            });

            const data = await response.json();

            if (response.ok) {
                this.showMessage('扫描已启动');
                this.monitorScanProgress();
            } else {
                this.showMessage(`启动扫描失败: ${data.error || '未知错误'}`, 'error');
                this.showProgress(false);
                this.isScanning = false;
            }
        } catch (error) {
            console.error('启动扫描失败:', error);
            this.showMessage('启动扫描失败', 'error');
            this.showProgress(false);
            this.isScanning = false;
        }
    }

    // 监控扫描进度
    async monitorScanProgress() {
        const checkProgress = async () => {
            try {
                const response = await fetch('/api/scan/status');
                const data = await response.json();

                if (response.ok) {
                    if (!data.is_scanning) {
                        // 扫描完成
                        this.showProgress(false);
                        this.isScanning = false;
                        this.showMessage('扫描完成！');
                        this.loadScanResults();
                    } else {
                        // 继续检查
                        setTimeout(checkProgress, 1000);
                    }
                } else {
                    this.showMessage('获取扫描状态失败', 'error');
                    this.showProgress(false);
                    this.isScanning = false;
                }
            } catch (error) {
                console.error('检查扫描进度失败:', error);
                this.showProgress(false);
                this.isScanning = false;
            }
        };

        // 开始检查
        setTimeout(checkProgress, 1000);
    }

    // 加载扫描结果
    async loadScanResults() {
        try {
            const response = await fetch('/api/scan/results');
            const data = await response.json();

            if (response.ok) {
                this.scanResults = data.results || [];
                this.displayScanResults();
            } else {
                console.error('加载扫描结果失败:', data.error);
            }
        } catch (error) {
            console.error('加载扫描结果失败:', error);
        }
    }

    // 显示扫描结果
    displayScanResults() {
        const resultsContainer = document.getElementById('scan-results');
        const countElement = document.getElementById('results-count');

        countElement.textContent = this.scanResults.length;

        if (this.scanResults.length === 0) {
            resultsContainer.innerHTML = '<div class="text-center text-muted py-4">暂无扫描结果</div>';
            return;
        }

        let html = '<div class="list-group">';

        this.scanResults.forEach(result => {
            html += `
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="mb-1">${this.escapeHtml(result.id)}</h6>
                            <p class="mb-1 text-muted">
                                <i class="fas fa-folder me-1"></i>${result.path}
                                ${result.file_count > 1 ? `<span class="badge bg-secondary ms-2">${result.file_count} 文件</span>` : ''}
                            </p>
                        </div>
                        <div class="text-end">
                            <div class="text-muted">${result.size_str}</div>
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        resultsContainer.innerHTML = html;
    }

    // 清空结果
    clearResults() {
        this.scanResults = [];
        this.displayScanResults();
        this.showMessage('结果已清空');
    }

    // HTML转义
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 启动应用
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new JavSPWebUI();
});