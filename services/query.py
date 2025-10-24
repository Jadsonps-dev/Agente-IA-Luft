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

    @staticmethod
    def query_status_op(id_depositante):
        """Consulta simplificada de acompanhamento de saída"""
        return f"""
        SELECT 
            vt.NOTAFISCAL,
            vt.CLASSIFICACAOTIPOPEDIDO,
            vt.STATUSNF,
            vt.IMPORTADOEM,
            vt.PESADOEM,
            vt.QTDETOTALPRODUTO,
            vt.DEPOSITANTE
        FROM (
            SELECT 
                nf.idnotafiscal,
                nf.codigointerno AS NOTAFISCAL,
                decode(nf.sequencia, 'K', 'W', nf.sequencia) AS SERIE,
                ctp.descricao AS CLASSIFICACAOTIPOPEDIDO,
                CASE
                    WHEN nfi.statusdoc = 0 THEN 'AG. FORMAÇÃO DE ROMANEIO/ONDA'
                    WHEN nfi.statusdoc = 8 THEN 'COLETA INICIADA'
                    WHEN nfi.statusdoc = 9 THEN 'EXPEDIDO'
                    WHEN (nfi.statusdoc = 10 OR
                        (nfi.statusdoc = 12 AND nf.datacancelamento IS NOT NULL AND nf.statusnf = 'X')) THEN
                        DECODE(nf.canceladoporerrointegracao, 1, 'ERRO DE INTEGRAÇÃO', 'CANCELADO')
                    WHEN nfi.statusdoc = 11 THEN 'QUARENTENA'
                    WHEN nf.statusnf = 'P' THEN 'PROCESSADO'
                    WHEN nfi.statusdoc = 12 AND nf.digitada = 'S' THEN 'DIGITADO'
                    WHEN nfi.statusdoc = 12 AND nf.digitada = 'N' AND nf.statusnf = 'I' THEN 'IMPORTADO'
                    WHEN nf.tiponf IN ('N','E') AND NVL(nf.impresso,'N') = 'S' THEN 'FATURADO'
                    WHEN nf.enviadofaturamento = 'S' THEN 'ENVIADO PARA FATURAMENTO'
                    ELSE 'AG. SEPARAÇÃO'
                END AS STATUSNF,
                nfi.dataimportacao AS IMPORTADOEM,
                decode(nvl(rp.tipo,0),0,rp.dtpesagemliberada,1,s.datapesagem) AS PESADOEM,
                (
                    SELECT SUM(NVL(nd.qtdefaturada, nd.qtdeatendida * e.fatorConversao))
                    FROM nfdet nd
                    JOIN embalagem e ON e.idproduto = nd.idproduto AND e.barra = nd.barra
                    WHERE nd.nf = nf.idnotafiscal
                ) AS QTDETOTALPRODUTO,
                d.razaosocial AS DEPOSITANTE
            FROM notafiscal nf
            LEFT JOIN nfimpressao nfi ON nfi.idprenf = nf.idprenf
            LEFT JOIN nfromaneio nfr ON nfr.idnotafiscal = nf.idnotafiscal
            LEFT JOIN romaneiopai rp ON rp.idromaneio = nfr.idromaneio
            LEFT JOIN vl_saidapornf s ON s.idnotafiscal = nfr.idnotafiscal AND s.idonda = nfr.idromaneio
            LEFT JOIN pontoalerta pa ON pa.idnotafiscal = nf.idnotafiscal
            LEFT JOIN usuario upa ON upa.idusuario = pa.idusuario
            LEFT JOIN usuario upal ON upal.idusuario = pa.idusuariolib
            LEFT JOIN classificacaotipopedido ctp ON ctp.idtipopedido = nf.idtipopedido
            LEFT JOIN entidade d ON d.identidade = nf.iddepositante
            WHERE nf.iddepositante = {id_depositante}
            AND UPPER(nf.movestoque) = 'S'
            AND NVL(nf.sequencia,' ') NOT IN ('AVARIA','PRODREC','AGCOB')
            AND TRUNC(nf.datacadastro) >= TO_DATE(&Data_Inicio,'dd/mm/yyyy')
            AND TRUNC(nf.datacadastro) <= TO_DATE(&Data_Fim,'dd/mm/yyyy')
        ) vt
        JOIN vt_itensnotafiscal i ON i.idnotafiscal = vt.idnotafiscal
        WHERE ( TO_DATE(DECODE(&Data_Fim,'null','',&Data_Fim),'DD/MM/YYYY') 
                - TO_DATE(DECODE(&Data_Inicio,'null','',&Data_Inicio),'DD/MM/YYYY') ) < 200
        """