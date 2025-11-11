import os
import re
import ftplib
from flask import Flask, request, render_template, send_file, jsonify
import requests
from io import BytesIO
import threading

app = Flask(__name__)

class FTPDownloader:
    @staticmethod
    def download_ftp_file(ftp_url, save_path=None):
        """Faz download de um arquivo FTP"""
        try:
            m = re.match(r'ftp://(?:(?P<user>[^:]+):(?P<pass>[^@]+)@)?(?P<host>[^/]+)(?P<path>/.*)', ftp_url)
            if not m:
                return False, "URL FTP inválida"
                
            gd = m.groupdict()
            user = gd['user'] or 'anonymous'
            passwd = gd['pass'] or 'anonymous@'
            host = gd['host']
            path = gd['path']
            
            # Conectar ao FTP
            ftp = ftplib.FTP(host, timeout=30)
            ftp.login(user=user, passwd=passwd)
            
            # Baixar para memória
            file_data = BytesIO()
            ftp.retrbinary(f'RETR {path}', file_data.write)
            ftp.quit()
            
            file_data.seek(0)
            return True, file_data
            
        except Exception as e:
            return False, f"Erro no download FTP: {str(e)}"

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
    
    # Se for URL FTP, faz download
    if url.lower().startswith('ftp://'):
        success, result = FTPDownloader.download_ftp_file(url)
        if success:
            # Retorna o arquivo para download
            filename = os.path.basename(url)
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        
        # Modifica links para passar pelo nosso proxy
        content = response.text
        content = re.sub(r'href="(ftp://[^"]+)"', r'href="/download?url=\1"', content)
        content = re.sub(r'href="(http://[^"]+)"', r'href="/navigate?url=\1"', content)
        content = re.sub(r'href="(https://[^"]+)"', r'href="/navigate?url=\1"', content)
        
        return content
        
    except Exception as e:
        return jsonify({'error': f'Erro ao acessar URL: {str(e)}'})

@app.route('/download')
def download():
    """Endpoint para download de arquivos FTP"""
    ftp_url = request.args.get('url', '')
    if not ftp_url:
        return jsonify({'error': 'URL FTP não fornecida'})
    
    success, result = FTPDownloader.download_ftp_file(ftp_url)
    if success:
        filename = os.path.basename(ftp_url)
        return send_file(
            result,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
    else:
        return jsonify({'error': result})

@app.route('/api/ftp-download')
def api_ftp_download():
    """API para download FTP (retorna JSON)"""
    ftp_url = request.args.get('url', '')
    if not ftp_url:
        return jsonify({'error': 'URL FTP não fornecida'})
    
    success, result = FTPDownloader.download_ftp_file(ftp_url)
    if success:
        return jsonify({
            'success': True,
            'message': 'Download concluído com sucesso',
            'filename': os.path.basename(ftp_url)
        })
    else:
        return jsonify({'success': False, 'error': result})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)