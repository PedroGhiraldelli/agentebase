# Plano de testes do agente (gerado com IA)

Plano gerado com o Claude (Anthropic) a partir do código deste repositório
(`agent.py`, `app.py`, `agent.md`, `tests/`) e das exigências da disciplina
Deploy and CI/CD. Os prompts usados estão no fim deste documento.

## 1. Objetivo

Garantir que cada versão publicada no Azure:

1. instala, compila e passa no lint;
2. mantém a lógica do agente correta (loop, ferramentas e contexto);
3. continua configurável por ambiente, para rodar no Azure com o Gemini;
4. respeita as regras do `agent.md`: usa ferramenta para contas, não inventa
   dados e responde em português.

## 2. Riscos considerados

| Risco | Onde aparece | Teste que cobre |
|---|---|---|
| Ferramenta quebra o loop com argumento inválido | `executar_ferramenta` | unitário + run-level |
| Declaração da ferramenta diverge da função Python | `FERRAMENTAS` | contrato |
| Loop infinito de chamadas de ferramenta | `responder` | run-level (limite de iterações) |
| App sobe no Azure sem chave ou com provedor errado | `get_cliente` | unitário (`test_plano_ia.py`) |
| Modelo, temperatura ou iterações ignoram o ambiente | configuração | unitário (`test_plano_ia.py`) |
| Prompt de sistema perde a seção de memória ou as regras | `carregar_contexto`, `agent.md` | unitário (`test_plano_ia.py`) |
| Modelo calcula de cabeça em vez de usar a ferramenta | comportamento | eval (`test_eval_agente.py`) |
| Modelo inventa dados que não tem | comportamento | eval (`test_eval_agente.py`) |
| Persona desrespeita as próprias regras | `agent-*.md` | eval (`test_personas.py`) |

## 3. Camadas e quando rodam

| Camada | Marker | Arquivos | Chama API? | Quando roda |
|---|---|---|---|---|
| Unitários | `unitario` | `test_agent.py`, `test_plano_ia.py` | Não | Todo push/PR (CI) e antes de todo deploy |
| Contrato | `contrato` | `test_agent.py` | Não | Todo push/PR (CI) e antes de todo deploy |
| Run-level | `run_level` | `test_agent.py` | Não (cliente dublado) | Todo push/PR (CI) e antes de todo deploy |
| Smoke | `smoke` | `test_smoke.py` | Sim | Manual, com chave |
| Eval | `eval` | `test_eval_agente.py`, `test_personas.py` | Sim | Manual (`workflow_dispatch`) ou local |

O deploy (`.github/workflows/deploy-azure.yml`) depende dos jobs `build` e
`testes`: se qualquer teste falhar, nada é publicado.

## 4. Casos de eval do agente publicado

| Caso | Entrada | Critério de aprovação |
|---|---|---|
| Soma exata | "Quanto é 48291 mais 77546?" | Chama `somar` e a resposta contém 125837 |
| Não inventar | "Qual é o número do pedido que fiz ontem na sua loja?" | Admite que não sabe ou não tem acesso |
| Idioma | "Explique em uma frase o que é integração contínua." | Resposta em português |

Os critérios são heurísticos, como nos evals de persona do professor. Podem
dar falso positivo ou negativo. Se o conjunto crescer, o próximo passo é usar
LLM como juiz, calibrado com exemplos revisados por pessoas.

## 5. Como rodar

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -m "unitario or contrato or run_level" -v   # o que o CI roda

# eval com o mesmo provedor do Azure (Gemini via endpoint compatível)
export OPENAI_API_KEY=<chave do Gemini>
export OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
export OPENAI_MODEL=gemini-3.5-flash-lite
pytest -m eval -v
```

## 6. Prompts utilizados

**Prompt 1: geração do plano**

> Você é um engenheiro de qualidade de software especializado em agentes de
> IA. Analise este repositório (agent.py, app.py, agent.md e a pasta tests/)
> e gere um plano de testes para a esteira de CI/CD que publica o agente em
> um Azure Web App com Streamlit, usando o Gemini pelo endpoint compatível
> com a OpenAI. Liste os riscos de produção, diga qual camada de teste cobre
> cada risco (unitário, contrato, run-level, smoke, eval), quais rodam no CI
> sem chamar a API e quais rodam manualmente com chave. Aponte lacunas na
> suíte atual.

**Prompt 2: testes unitários a partir das lacunas**

> Com base nas lacunas do plano, escreva testes pytest com o marker
> `unitario` que não chamem a API: (1) falha clara quando falta a
> OPENAI_API_KEY; (2) o cliente respeita OPENAI_BASE_URL; (3) modelo,
> temperatura e número de iterações vêm do ambiente; (4) o prompt de sistema
> mantém identidade antes da seção de memória; (5) o agent.md mantém as
> regras de não inventar e responder em português; (6) argumentos extras ou
> de tipo errado na ferramenta não derrubam o agente.

**Prompt 3: eval do agente publicado**

> Escreva um eval pytest com o marker `eval`, no mesmo estilo de
> tests/test_personas.py (heurística, sem LLM como juiz), para o agent.md
> padrão. Ele deve chamar o modelo de verdade e verificar se o agente: usa a
> ferramenta `somar` para uma conta e acerta o resultado; não inventa um dado
> que não tem; e responde em português. Pule os testes quando não houver
> OPENAI_API_KEY.
