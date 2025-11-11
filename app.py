import os
import re
import ftplib
from flask import Flask, request, render_template, send_file, jsonify
import requests
from io import BytesIO
import logging
from urllib.parse import urljoin

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class FTPDownloader:
    @staticmethod
    def download_ftp_file(ftp_url):
        """Faz download de um arquivo FTP"""
        try:
            logger.info(f"Iniciando download FTP: {ftp_url}")
            
            m = re.match(r'ftp://(?:(?P<user>[^:]+):(?P<pass>[^@]+)@)?(?P<host>[^/]+)(?P<path>/.*)', ftp_url)
            if not m:
                return False, "URL FTP inválida"
                
            gd = m.groupdict()
            user = gd['user'] or 'anonymous'
            passwd = gd['pass'] or 'anonymous@'
            host = gd['host']
            path = gd['path']
            
            logger.info(f"Conectando ao FTP: {host}")
            
            # Conectar ao FTP
            ftp = ftplib.FTP(host, timeout=30)
            ftp.login(user=user, passwd=passwd)
            
            # Baixar para memória
            file_data = BytesIO()
            
            def callback(data):
                file_data.write(data)
            
            ftp.retrbinary(f'RETR {path}', callback)
            ftp.quit()
            
            file_data.seek(0)
            logger.info(f"Download FTP concluído: {len(file_data.getvalue())} bytes")
            return True, file_data
            
        except Exception as e:
            error_msg = f"Erro no download FTP: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

def replace_links(content, base_url):
    """Substitui links no conteúdo HTML para passar pelo proxy"""
    # Substituir links FTP
    content = re.sub(
        r'href="(ftp://[^"]+)"', 
        r'href="/download?url=\1"', 
        content, 
        flags=re.IGNORECASE
    )
    
    # Substituir links HTTP/HTTPS relativos
    def replace_http_link(match):
        link = match.group(1)
        if link.startswith(('http://', 'https://', 'ftp://', '#', 'javascript:')):
            return match.group(0)  # Mantém o link original
        else:
            # Link relativo - converte para absoluto
            absolute_url = urljoin(base_url, link)
            return f'href="/navigate?url={absolute_url}"'
    
    content = re.sub(r'href="([^"]+)"', replace_http_link, content)
    
    # Substituir ações de formulário
    def replace_form_action(match):
        action = match.group(1)
        if action.startswith(('http://', 'https://', '#')):
            return match.group(0)  # Mantém a ação original
        else:
            # Ação relativa - converte para absoluta
            absolute_url = urljoin(base_url, action)
            return f'action="/navigate?url={absolute_url}"'
    
    content = re.sub(r'action="([^"]+)"', replace_form_action, content)
    
    return content

@app.route('/')
def index():
    """Página inicial com navegador embutido"""
    return render_template('index.html')

@app.route('/navigate')
def navigate():
    """Navega para uma URL"""
    url = request.args.get('url', '')
    if not url:
        return jsonify({'error': 'URL não fornecida'})
    
    logger.info(f"Navegando para: {url}")
    
    # Se for URL FTP, faz download
    if url.lower().startswith('ftp://'):
        success, result = FTPDownloader.download_ftp_file(url)
        if success:
            # Retorna o arquivo para download
            filename = os.path.basename(url) or "download.dat"
            return send_file(
                result,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
        else:
            return jsonify({'error': result})
    
    # Se for HTTP/HTTPS, faz proxy
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        
        # Modifica links para passar pelo nosso proxy
        content = response.text
        content = replace_links(content, url)
        
        return content
        
    except requests.exceptions.RequestException as e:
        error_msg = f'Erro ao acessar URL: {str(e)}'
        logger.error(error_msg)
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Erro ao carregar a página</h2>
                <p>{error_msg}</p>
                <a href="/">Voltar para página inicial</a>
            </body>
        </html>
        """
    except Exception as e:
        error_msg = f'Erro inesperado: {str(e)}'
        logger.error(error_msg)
        return jsonify({'error': error_msg})

@app.route('/download')
def download():
    """Endpoint para download de arquivos FTP"""
    ftp_url = request.args.get('url', '')
    if not ftp_url:
        return jsonify({'error': 'URL FTP não fornecida'})
    
    logger.info(f"Download FTP solicitado: {ftp_url}")
    
    success, result = FTPDownloader.download_ftp_file(ftp_url)
    if success:
        filename = os.path.basename(ftp_url) or "download.dat"
        return send_file(
            result,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    else:
        return jsonify({'error': result})

@app.route('/health')
def health():
    """Endpoint de health check"""
    return jsonify({'status': 'healthy', 'service': 'navegador-ftp'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Iniciando servidor na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)