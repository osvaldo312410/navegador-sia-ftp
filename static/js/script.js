function go(){
    const url = document.getElementById('urlInput').value;
    if (url.trim() !== '') {
        window.location.href = url;
    }
}

// Focar no input quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('urlInput').focus();
});

// Permitir Enter para enviar
document.getElementById('urlInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        go();
    }
});