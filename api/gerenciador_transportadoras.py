
from api.api_dialogo import DialogoTransportadora
import logging

logger = logging.getLogger(__name__)


class GerenciadorTransportadoras:
    """
    Gerenciador central para consultas de rastreamento em múltiplas transportadoras.
    """
    
    def __init__(self):
        # Registrar todas as transportadoras disponíveis
        self.transportadoras = {
            'dialogo': DialogoTransportadora(),
            # Adicione novas transportadoras aqui:
            # 'jadlog': JadlogTransportadora(),
            # 'correios': CorreiosTransportadora(),
        }
        self.logger = logger
    
    def consultar_transportadora(self, nome_transportadora: str, cnpj_destinatario: str) -> dict:
        """
        Consulta uma transportadora específica.
        
        Args:
            nome_transportadora: Nome da transportadora (ex: 'dialogo', 'jadlog')
            cnpj_destinatario: CNPJ do destinatário
            
        Returns:
            dict com resultado da consulta
        """
        transportadora_key = nome_transportadora.lower()
        
        if transportadora_key not in self.transportadoras:
            return {
                'sucesso': False,
                'erro': f'Transportadora "{nome_transportadora}" não encontrada.',
                'transportadoras_disponiveis': list(self.transportadoras.keys())
            }
        
        transportadora = self.transportadoras[transportadora_key]
        self.logger.info(f"Consultando {transportadora.get_nome_transportadora()} para CNPJ: {cnpj_destinatario}")
        
        return transportadora.consultar_rastreio(cnpj_destinatario)
    
    def listar_transportadoras(self) -> list:
        """Retorna lista de transportadoras disponíveis"""
        return [
            {
                'codigo': codigo,
                'nome': transportadora.get_nome_transportadora()
            }
            for codigo, transportadora in self.transportadoras.items()
        ]


# Exemplo de uso
if __name__ == '__main__':
    gerenciador = GerenciadorTransportadoras()
    
    # Listar transportadoras disponíveis
    print("Transportadoras disponíveis:")
    for t in gerenciador.listar_transportadoras():
        print(f"  - {t['codigo']}: {t['nome']}")
    
    # Consultar Dialogo
    print("\nConsultando Dialogo:")
    resultado = gerenciador.consultar_transportadora('dialogo', '00449498042')
    print(resultado)
