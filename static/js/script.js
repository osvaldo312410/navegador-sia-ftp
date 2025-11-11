let currentUrl = 'http://sia.datasus.gov.br/principal/index.php';
        
        function navigateToUrl() {
            const urlInput = document.getElementById('urlInput');
            let url = urlInput.value.trim();
            
            if (!url) return;
            
            if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('ftp://')) {
                url = 'http://' + url;
                urlInput.value = url;
            }
            
            currentUrl = url;
            
            if (url.startsWith('ftp://')) {
                // Download direto para links FTP
                showStatus('Iniciando download FTP...', 'success');
                window.location.href = '/download?url=' + encodeURIComponent(url);
            } else {
                // Navegação normal para HTTP/HTTPS
                showStatus('Carregando...', 'success');
                document.getElementById('browserFrame').src = '/navigate?url=' + encodeURIComponent(url);
            }
        }
        
        function showStatus(message, type) {
            const statusDiv = document.getElementById('statusMessage');
            statusDiv.innerHTML = `<div class="status-message ${type}">${message}</div>`;
            setTimeout(() => {
                statusDiv.innerHTML = '';
            }, 5000);
        }
        
        // Enter para navegar
        document.getElementById('urlInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                navigateToUrl();
            }
        });
        
        // Atualizar barra de URL quando o iframe mudar
        document.getElementById('browserFrame').addEventListener('load', function() {
            document.getElementById('urlInput').value = currentUrl;
        });