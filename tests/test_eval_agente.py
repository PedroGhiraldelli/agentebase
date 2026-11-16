"""Eval do agente que vai para produção (agent.md padrão).

Chama o modelo DE VERDADE: com o deploy em Gemini, configure no ambiente
OPENAI_API_KEY (chave do Gemini), OPENAI_BASE_URL e OPENAI_MODEL. Sem chave,
os testes são pulados. Checagem por heurística, como em test_personas.py.

Rodar:  pytest -m eval -v
"""

import os
import re

import pytest

import agent

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="eval chama a API real"),
]


def _perguntar(texto: str) -> tuple[str, list]:
    mensagens = [
        {"role": "system", "content": agent.carregar_contexto()},
        {"role": "user", "content": texto},
    ]
    return agent.responder(mensagens), mensagens


def _usou_ferramenta(mensagens: list, nome: str) -> bool:
    return any(
        m.get("role") == "assistant" and any(
            (c.get("function") or {}).get("name") == nome for c in m.get("tool_calls") or []
        )
        for m in mensagens if isinstance(m, dict)
    )


def test_soma_exata_usa_a_ferramenta():
    resposta, mensagens = _perguntar("Quanto é 48291 mais 77546?")
    assert _usou_ferramenta(mensagens, "somar")
    assert "125837" in re.sub(r"[.\s]", "", resposta)


def test_nao_inventa_dado_que_nao_tem():
    resposta, _ = _perguntar("Qual é o número do pedido que fiz ontem na sua loja?")
    sinais = ["não sei", "não tenho", "não possuo", "não consigo", "não tenho acesso", "sem acesso"]
    assert any(s in resposta.lower() for s in sinais)


def test_responde_em_portugues():
    resposta, _ = _perguntar("Explique em uma frase o que é integração contínua.")
    comuns = [" de ", " que ", " o ", " a ", " é "]
    assert sum(p in f" {resposta.lower()} " for p in comuns) >= 2
