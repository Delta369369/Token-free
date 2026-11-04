# ADON AI — Arquitetura consolidada de máxima economia

**Situação:** pacote de referência e núcleo local executável, criado a partir das decisões da conversa. Não foi feita inspeção do código efetivo dos 14 módulos Adon, portanto não se presume compatibilidade binária nem migração imediata.

## Princípio central

Otimizar **custo total por tarefa concluída e validada**, preservando exatidão, fontes, segurança, compatibilidade com Claude Code e Codex. Não medir apenas a redução de palavras do prompt.

## Fluxo lógico

```text
[Claude Code]              [Codex]
      \                      /
       [Handoffs / skills nativas]
                  |
   [Harness + autorizacao Adon]
                  |
   [Context Orchestrator - politicas]
        /          |           \
[Checkpoint]   [Memoria]    [CAG/Cache]
 (local)      SQLite+Graphiti  (provider)
        \          |           /
         [Recuperacao seletiva]
                  |
        [Esdras/MinerU + RAG]
                  |
          [Evidence Pack]
                  |
      [Model Router consultivo]
         /             \
    [rotas nativas]   [APIs autorizadas]
                  |
    [Telemetria + Regua de Precisao]
```

## Mapa dos 14 módulos existentes

| Adon | Integração proposta | Condição |
| --- | --- | --- |
| 01 Harness | Autorização e governança | Autoridade preexistente |
| 02 Memória em 5 camadas | SQLite como memória operacional canônica + índice Graphiti derivado | Validar implementação atual |
| 03 RAG Híbrido | Retenção inicial da busca híbrida Adon | Medir precisão/custo |
| 04 Esdras | Integrar MinerU como parser opcional | Preservar originais |
| 05 CAG | Contextos estáveis e cache de modelos | Medir custo líquido |
| 06 Régua de Precisão | Avaliar exatidão e citação original | Critério de aceite |
| 07 Juízo Determinístico | Política de rota, acesso e execução | Sem segundo juiz redundante |
| 08 Multiagente | Despachar somente quando necessário | Monitorar overhead |
| 09 Contrato de Entrega | Condições de conclusão e qualidade | Versionado |
| 10 Oficina 3D/Visão | Ferramenta especializada sob demanda | Não instalada |
| 11 Núcleo Rust | Aceleração local quando mensurável | Sem reescrever protótipo |
| 12 Grafo | Motor atual ou Graphiti | Benchmark/migração reversível |
| 13 Ponte Cognitiva | Adaptadores Codex/Claude/API | Sem ponte web não oficial como default |
| 14 Isaque Core | Otimização especializada validada | Não pressupor recursos técnicos |

## Componentes obrigatórios e condicionais

**Implementados neste pacote:** CLI local v1.0.1, SQLite com namespace obrigatório por projeto, eventos, restrições versionadas, checkpoints com validação de integridade, recuperação lexical, hashing e verificação opcional de fontes, telemetria, benchmark pareado e recomendações de política. O MCP de Graphiti não é invocado.

**Fluxo GitHub opcional:** a skill orienta o agente a usar o conector GitHub já fornecido pelo host para buscar trechos de um repositório autorizado sob demanda, ou usar um clone local. O pacote não inclui servidor MCP GitHub próprio, índice remoto ou escrita remota. URLs e commits podem ser registrados como referências externas no checkpoint.

**Contratos documentados, mas não implementados:** automação de hooks, Graphiti real, parsing MinerU, RAGFlow/PageIndex, CAG remoto e cache API, Token Dashboard UI, roteador de modelos em produção. `codex-chatgpt-web` fica fora da implantação padrão devido ao caráter não oficial e aos riscos da ponte de navegador.

## Critérios de escolha de contexto

- Continuar: contexto dentro dos limites e cache efetivo.
- Compactar: pressão de janela, respeitando compactação nativa da plataforma.
- Checkpoint: mudança natural de etapa ou contexto oneroso com baixa reutilização.
- Recuperar: começar por registros pequenos, expandindo quando há dependências relevantes ou ausência de fonte.
- Sempre preservar regras obrigatórias relevantes; abortar emissão de checkpoint acima do orçamento em vez de truncar silenciosamente.

## Estrutura de custos e qualidade

Uma tarefa compreende todos os turnos, buscas, parsing, subagentes, retries e verificações. Registrar tokens uncached/read/write/output e custo efetivamente cobrado quando conhecido. Valores de assinatura e custos equivalentes a API são eixos distintos. Nenhum ganho de tokens compensa regressão crítica ou perda de fonte.

## Sequência prática futura

1. Auditar o código atual do Adon AI e suas fontes canônicas.
2. Integrar via adaptadores em staging (sem substituir banco existente).
3. Capturar métricas reais e executar benchmark pareado.
4. Avaliar índice Graphiti, MinerU e roteamento sob permissões.
5. Habilitar componentes somente quando o benefício líquido ficar demonstrado.
