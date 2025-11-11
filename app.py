import sys
import re
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLineEdit, QToolBar, QAction,
    QFileDialog, QMessageBox, QWidget, QVBoxLayout, QTabWidget
)
from PyQt5.QtCore import QUrl, QObject, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from ftplib import FTP


class FTPInterceptor(QWebEngineUrlRequestInterceptor):
    """Intercepta requisições FTP e faz o download direto."""
    def __init__(self, parent=None, log_callback=None, navigation_callback=None):
        super().__init__(parent)
        self.log_callback = log_callback
        self.navigation_callback = navigation_callback
        self.processed_urls = set()
        self.current_page_url = ""

    def set_current_page_url(self, url):
        """Define a URL atual da página para voltar após o download"""
        self.current_page_url = url

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        
        # Interceptar apenas URLs FTP
        if (url.lower().startswith("ftp://") and 
            url not in self.processed_urls):
            
            self.processed_urls.add(url)
            info.block(True)  # Bloqueia a navegação para a URL FTP
            
            if self.log_callback:
                self.log_callback(f"Interceptado link FTP: {url}")
            
            # Salvar a URL atual antes do download
            current_url = self.current_page_url
            
            # Processar o download
            QTimer.singleShot(100, lambda: self.download_ftp(url, current_url))
            
            # Limpar da lista após um tempo
            QTimer.singleShot(5000, lambda: self.processed_urls.discard(url))

    def download_ftp(self, url, previous_url):
        try:
            m = re.match(r'ftp://(?:(?P<user>[^:]+):(?P<pass>[^@]+)@)?(?P<host>[^/]+)(?P<path>/.*)', url)
            if not m:
                if self.log_callback:
                    self.log_callback(f"URL FTP inválida: {url}")
                return
                
            gd = m.groupdict()
            user = gd['user'] or 'anonymous'
            passwd = gd['pass'] or 'anonymous@'
            host = gd['host']
            path = gd['path']
            
            filename = os.path.basename(path) or "download_ftp"
            local_path, _ = QFileDialog.getSaveFileName(
                None, 
                f"Salvar arquivo FTP - {filename}",
                os.path.expanduser(f"~/Downloads/{filename}")
            )
            
            if not local_path:
                if self.log_callback:
                    self.log_callback("Download cancelado pelo usuário")
                # Voltar para a página anterior mesmo se cancelar
                if self.navigation_callback and previous_url:
                    QTimer.singleShot(100, lambda: self.navigation_callback(previous_url))
                return
                
            if self.log_callback:
                self.log_callback(f'Conectando a {host} ...')
                
            ftp = FTP(host, timeout=30)
            ftp.login(user=user, passwd=passwd)
            
            with open(local_path, 'wb') as f:
                if self.log_callback:
                    self.log_callback(f'Baixando {path} ...')
                ftp.retrbinary(f'RETR {path}', f.write)
                
            ftp.quit()
            
            if self.log_callback:
                file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
                self.log_callback(f"✅ Download concluído: {local_path} ({file_size_mb:.2f} MB)")
            
            # Voltar para a página anterior após o download
            if self.navigation_callback and previous_url:
                QTimer.singleShot(100, lambda: self.navigation_callback(previous_url))
                
            QMessageBox.information(None, "Download Concluído", 
                                  f"Arquivo salvo em:\n{local_path}\n\n"
                                  f"Tamanho: {os.path.getsize(local_path) / (1024 * 1024):.2f} MB")
            
        except Exception as e:
            error_msg = f"Erro no download FTP: {str(e)}"
            if self.log_callback:
                self.log_callback(f"❌ {error_msg}")
            
            # Voltar para a página anterior mesmo em caso de erro
            if self.navigation_callback and previous_url:
                QTimer.singleShot(100, lambda: self.navigation_callback(previous_url))
                
            QMessageBox.critical(None, "Erro no Download", error_msg)


class BrowserTab(QWebEngineView):
    """Classe para representar uma aba do navegador"""
    def __init__(self, interceptor, parent=None):
        super().__init__(parent)
        self.interceptor = interceptor
        QWebEngineProfile.defaultProfile().setUrlRequestInterceptor(self.interceptor)


class ModernFTPNavigator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌐 Navegador FTP Moderno - SIA Datasus")
        self.resize(1200, 800)

        # Widget de abas
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.setCentralWidget(self.tabs)

        # Interceptador com callback de navegação
        self.interceptor = FTPInterceptor(
            log_callback=self.log_message,
            navigation_callback=self.navigate_to_url
        )

        # Barra de ferramentas
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Ações
        new_tab_btn = QAction("➕ Nova Aba", self)
        back_btn = QAction("⏪ Voltar", self)
        forward_btn = QAction("⏩ Avançar", self)
        reload_btn = QAction("🔄 Recarregar", self)
        home_btn = QAction("🏠 SIA Datasus", self)

        toolbar.addAction(new_tab_btn)
        toolbar.addSeparator()
        toolbar.addAction(back_btn)
        toolbar.addAction(forward_btn)
        toolbar.addAction(reload_btn)
        toolbar.addAction(home_btn)

        # Campo de endereço
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Digite o endereço (http://, https:// ou ftp://)...")
        self.url_bar.returnPressed.connect(self.load_url)
        toolbar.addWidget(self.url_bar)

        # Barra de status
        self.statusBar().showMessage("Pronto para navegar...")

        # Conexões
        new_tab_btn.triggered.connect(self.create_new_tab)
        back_btn.triggered.connect(self.navigate_back)
        forward_btn.triggered.connect(self.navigate_forward)
        reload_btn.triggered.connect(self.reload_current)
        home_btn.triggered.connect(self.load_home)

        # Criar primeira aba com SIA Datasus
        self.create_new_tab("http://sia.datasus.gov.br/principal/index.php", "SIA Datasus")

    def navigate_to_url(self, url):
        """Navega para uma URL específica na aba atual"""
        current = self.current_tab()
        if current and url:
            current.load(QUrl(url))

    def create_new_tab(self, url=None, title="Nova Aba"):
        """Cria uma nova aba"""
        new_tab = BrowserTab(self.interceptor)
        
        if url:
            new_tab.load(QUrl(url))
        
        # Conectar sinais
        new_tab.urlChanged.connect(lambda url: self.on_url_changed(url, new_tab))
        new_tab.loadStarted.connect(self.load_started)
        new_tab.loadFinished.connect(self.load_finished)
        
        index = self.tabs.addTab(new_tab, title)
        self.tabs.setCurrentIndex(index)
        
        return new_tab

    def on_url_changed(self, url, tab):
        """Quando a URL muda em uma aba"""
        # Atualizar a barra de URL
        self.update_url_bar(url, tab)
        
        # Atualizar a URL atual no interceptador (apenas para a aba atual)
        if tab == self.current_tab():
            self.interceptor.set_current_page_url(url.toString())

    def close_tab(self, index):
        """Fecha uma aba"""
        if self.tabs.count() > 1:
            self.tabs.widget(index).deleteLater()
            self.tabs.removeTab(index)

    def current_tab(self):
        """Retorna a aba atual"""
        return self.tabs.currentWidget()

    def current_tab_changed(self, index):
        """Quando muda de aba"""
        if index >= 0:
            current_tab = self.current_tab()
            if current_tab:
                url = current_tab.url()
                self.update_url_bar(url, current_tab)
                self.interceptor.set_current_page_url(url.toString())

    def navigate_back(self):
        """Volta para página anterior"""
        current = self.current_tab()
        if current:
            current.back()

    def navigate_forward(self):
        """Avança para próxima página"""
        current = self.current_tab()
        if current:
            current.forward()

    def reload_current(self):
        """Recarrega a página atual"""
        current = self.current_tab()
        if current:
            current.reload()

    def log_message(self, msg):
        """Log de mensagens"""
        print(msg)
        self.statusBar().showMessage(msg, 5000)

    def load_started(self):
        """Quando começa a carregar"""
        self.statusBar().showMessage("Carregando...")

    def load_finished(self, success):
        """Quando termina de carregar"""
        current_tab = self.current_tab()
        if current_tab:
            if success:
                self.statusBar().showMessage("Página carregada com sucesso", 3000)
                # Atualizar título da aba
                title = current_tab.page().title()
                if title:
                    index = self.tabs.indexOf(current_tab)
                    short_title = title[:25] + "..." if len(title) > 25 else title
                    self.tabs.setTabText(index, short_title)
            else:
                self.statusBar().showMessage("Erro ao carregar a página", 3000)

    def update_url_bar(self, url, tab=None):
        """Atualiza a barra de URL"""
        # Só atualizar se for a aba atual
        if not tab or tab == self.current_tab():
            self.url_bar.setText(url.toString())

    def load_home(self):
        """Carrega SIA Datasus na aba atual"""
        current = self.current_tab()
        if current:
            sia_url = "http://sia.datasus.gov.br/principal/index.php"
            current.load(QUrl(sia_url))

    def load_url(self):
        """Carrega a URL digitada na barra de endereços"""
        url = self.url_bar.text().strip()
        if not url:
            return
            
        if not url.startswith(("http://", "https://", "ftp://")):
            url = "http://" + url
            
        current = self.current_tab()
        if current:
            current.load(QUrl(url))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = ModernFTPNavigator()
    win.show()
    sys.exit(app.exec_())