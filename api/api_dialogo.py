
import re
from api.base_transportadora import BaseTransportadora


class DialogoTransportadora(BaseTransportadora):
    """
    Classe para consulta de rastreamento na transportadora Dialogo Logística.
    """
    
    def __init__(self):
        super().__init__()
        self.url_inicial = "https://ssw.inf.br/2/ssw_resultSSW_dest"
        self.sigla_emp = "DLG"
    
    def get_nome_transportadora(self) -> str:
        return "Dialogo Logística"
    
    def consultar_rastreio(self, cnpj_destinatario: str) -> dict:
        """
        Consulta rastreamento de pedidos na Dialogo Logística.
        
        Args:
            cnpj_destinatario: CNPJ do destinatário (sem pontos e traços)
            
        Returns:
            dict com informações do rastreamento ou erro
        """
        try:
            # Limpar CNPJ (remover caracteres não numéricos)
            cnpj_limpo = re.sub(r'[^0-9]', '', cnpj_destinatario)
            
            if not cnpj_limpo or len(cnpj_limpo) != 11:
                return {
                    'sucesso': False,
                    'erro': 'CNPJ inválido. Deve conter 11 dígitos.',
                    'transportadora': self.get_nome_transportadora()
                }
            
            self.logger.info(f"Consultando rastreio Dialogo para CNPJ: {cnpj_limpo}")
            
            # Primeira requisição para obter o link de detalhes
            headers_inicial = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0",
                "Origin": "https://dialogologistica.com.br",
                "Referer": "https://dialogologistica.com.br/",
            }
            
            payload = {
                "urlori": "https://dialogologistica.com.br/rastreie-seu-pedido",
                "sigla_emp": self.sigla_emp,
                "cnpjdest": cnpj_limpo
            }
            
            response = self._fazer_requisicao_post(
                self.url_inicial,
                headers_inicial,
                payload,
                encoding="iso-8859-1"
            )
            
            # Buscar o link de detalhes na resposta
            onclick_regex = re.compile(r"opx\('/2/ssw_SSWDetalhado\?id=([^&]+)&md=([^']+)'\)")
            match = onclick_regex.search(response.text)
            
            if not match:
                return {
                    'sucesso': False,
                    'erro': 'Nenhum pedido encontrado para este CNPJ.',
                    'transportadora': self.get_nome_transportadora()
                }
            
            id_param, md_param = match.groups()
            url_detalhado = f"https://ssw.inf.br/2/ssw_SSWDetalhado?id={id_param}&md={md_param}"
            
            # Segunda requisição para obter detalhes
            headers_detalhado = {
                "User-Agent": "Mozilla/5.0",
                "Referer": self.url_inicial,
            }
            
            resp_detalhado = self._fazer_requisicao_get(
                url_detalhado,
                headers_detalhado,
                encoding="iso-8859-1"
            )
            
            # Extrair informações
            linhas = self._extrair_texto_soup(resp_detalhado.text)
            
            return {
                'sucesso': True,
                'transportadora': self.get_nome_transportadora(),
                'cnpj_consultado': cnpj_limpo,
                'detalhes': linhas,
                'url_rastreio': url_detalhado
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao consultar Dialogo: {str(e)}")
            return {
                'sucesso': False,
                'erro': f'Erro ao consultar transportadora: {str(e)}',
                'transportadora': self.get_nome_transportadora()
            }


# Para manter compatibilidade com código existente (se necessário)
if __name__ == '__main__':
    dialogo = DialogoTransportadora()
    resultado = dialogo.consultar_rastreio("00449498042")
    
    if resultado['sucesso']:
        print(f"\n✓ Rastreio encontrado na {resultado['transportadora']}:\n")
        for linha in resultado['detalhes']:
            print(linha)
    else:
        print(f"\n✗ Erro: {resultado['erro']}")
