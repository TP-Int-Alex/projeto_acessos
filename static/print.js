document.addEventListener('DOMContentLoaded', function() {
    const menuItems = document.querySelectorAll('.print-menu-item');
    const formPrint = document.getElementById('formPrint');
    const btnSubmit = document.getElementById('btnSubmitPrint');
    
    menuItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault(); 
            
            menuItems.forEach(i => i.classList.remove('active'));
            this.classList.add('active');
            
            const tipo = this.getAttribute('data-tipo');
            
            if (tipo === 'planilha') {
                formPrint.setAttribute('action', '/clientes/excel');
                formPrint.setAttribute('target', '_blank');
                btnSubmit.innerText = 'Gerar Planilha';
            } else {
                formPrint.setAttribute('action', '/clientes/imprimir');
                formPrint.setAttribute('target', '_blank');
                btnSubmit.innerText = 'Gerar PDF';
            }
        });
    });
});