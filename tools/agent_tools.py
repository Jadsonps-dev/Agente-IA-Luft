
"""
Definições de tools (ferramentas) para o agente de IA.
Contém as especificações de function calling da OpenAI.
"""


def get_consulta_nf_tool():
    """
    Retorna a definição da tool para consultar nota fiscal.
    """
    return {
        "type": "function",
        "function": {
            "name": "consultar_nota_fiscal_wms",
            "description": "Busca informações de uma nota fiscal específica no WMS da Luft Solutions",
            "parameters": {
                "type": "object",
                "properties": {
                    "tipo_consulta": {
                        "type": "string",
                        "enum": ["nota_fiscal"],
                        "description": "Tipo de consulta - sempre 'nota_fiscal'"
                    },
                    "numero_nf": {
                        "type": "string",
                        "description": "Número da nota fiscal fornecido pelo usuário"
                    },
                    "empresa": {
                        "type": "string",
                        "enum": ["Insider", "Alpargatas", "todas"],
                        "description": "Nome da empresa mencionada: Insider, Alpargatas ou todas"
                    },
                    "id_depositante": {
                        "type": "string",
                        "enum": ["2361178", "538607"],
                        "description": "ID do depositante: 2361178=Insider | 538607=Alpargatas"
                    }
                },
                "required": ["tipo_consulta", "numero_nf"]
            }
        }
    }


def get_all_tools():
    """
    Retorna lista com todas as tools disponíveis para o agente.
    """
    return [
        get_consulta_nf_tool()
    ]
