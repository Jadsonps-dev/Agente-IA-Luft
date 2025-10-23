class Queries:
    def __init__(self):
        pass
    
    @staticmethod
    def query_nf(id_depositante, nota_fiscal):
        """Consulta simplificada de acompanhamento de saída"""
        return f"""
        SELECT 
            nf.codigointerno AS "Nota Fiscal",
            
            CASE
                WHEN nfi.statusdoc = 0 THEN 'AG. FORMAÇÃO DE ROMANEIO/ONDA'
                WHEN nfi.statusdoc = 8 THEN 'COLETA INICIADA'
                WHEN nfi.statusdoc = 9 THEN 'EXPEDIDO'
                WHEN (nfi.statusdoc = 10 OR (nfi.statusdoc = 12 AND nf.datacancelamento IS NOT NULL AND nf.statusnf = 'X'))
                    THEN DECODE(nf.canceladoporerrointegracao, 1, 'ERRO DE INTEGRAÇÃO', 'CANCELADO')
                WHEN nfi.statusdoc = 11 THEN 'QUARENTENA'
                WHEN nf.statusnf = 'P' THEN 'PROCESSADO'
                WHEN nfi.statusdoc = 12 AND nf.digitada = 'S' THEN 'DIGITADO'
                WHEN nfi.statusdoc = 12 AND nf.digitada = 'N' AND nf.statusnf = 'I' THEN 'IMPORTADO'
                WHEN nf.tiponf IN ('N', 'E') AND NVL(nf.impresso, 'N') = 'S' THEN 'FATURADO'
                WHEN nf.enviadofaturamento = 'S' THEN 'ENVIADO PARA FATURAMENTO'
                ELSE 'AG. SEPARAÇÃO'
            END AS "Status da Nota Fiscal",

            t.razaosocial AS "Transportadora",
            nf.codigorastreio AS "Código Rastreio"

        FROM notafiscal nf
        JOIN nfimpressao nfi ON nfi.idprenf = nf.idprenf
        LEFT JOIN entidade t ON t.identidade = nf.transportadoranotafiscal

        WHERE nf.iddepositante = {id_depositante}
          AND nf.codigointerno = '{nota_fiscal}'
        """