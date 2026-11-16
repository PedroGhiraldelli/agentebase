"""Testes derivados do plano gerado com IA (docs/PLANO_DE_TESTES.md).

Complementam tests/test_agent.py cobrindo pontos que o plano apontou como
riscos de produção e que ainda não tinham teste: configuração por variável
de ambiente (necessária para o deploy no Azure com Gemini) e o formato do
prompt de sistema.

Nenhum teste aqui chama a API: rodam no CI de todo push e PR.
"""

import importlib
import json

import pytest

import agent


@pytest.mark.unitario
class TestConfiguracaoPorAmbiente:
    def test_sem_chave_falha_com_mensagem_clara(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setattr(agent, "_cliente", None)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            agent.get_cliente()

    def test_aceita_gemini_api_key_quando_nao_ha_openai_api_key(self, monkeypatch):
        # No Azure a chave do Gemini pode estar cadastrada como GEMINI_API_KEY.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "chave-gemini-de-teste")
        monkeypatch.setattr(agent, "_cliente", None)
        assert agent.get_cliente().api_key == "chave-gemini-de-teste"
        monkeypatch.setattr(agent, "_cliente", None)

    def test_cliente_respeita_base_url_do_provedor(self, monkeypatch):
        # No Azure o app aponta para o endpoint compatível do Gemini só por variável.
        url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        monkeypatch.setenv("OPENAI_API_KEY", "chave-de-teste")
        monkeypatch.setenv("OPENAI_BASE_URL", url)
        monkeypatch.setattr(agent, "_cliente", None)
        cliente = agent.get_cliente()
        assert str(cliente.base_url) == url
        monkeypatch.setattr(agent, "_cliente", None)

    def test_modelo_temperatura_e_iteracoes_vem_do_ambiente(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gemini-3.5-flash-lite")
        monkeypatch.setenv("AGENTE_TEMPERATURA", "0.2")
        monkeypatch.setenv("AGENTE_MAX_ITERACOES", "3")
        recarregado = importlib.reload(agent)
        try:
            assert recarregado.MODELO == "gemini-3.5-flash-lite"
            assert recarregado.TEMPERATURA == 0.2
            assert recarregado.MAX_ITERACOES == 3
        finally:
            monkeypatch.delenv("OPENAI_MODEL")
            monkeypatch.delenv("AGENTE_TEMPERATURA")
            monkeypatch.delenv("AGENTE_MAX_ITERACOES")
            importlib.reload(agent)


@pytest.mark.unitario
class TestPromptDeSistema:
    def test_contexto_tem_secao_de_memoria_separada(self, tmp_path, monkeypatch):
        (tmp_path / "agent.md").write_text("Identidade X", encoding="utf-8")
        (tmp_path / "memory.md").write_text("Fato Y", encoding="utf-8")
        monkeypatch.setattr(agent, "AGENT_MD", tmp_path / "agent.md")
        monkeypatch.setattr(agent, "MEMORY_MD", tmp_path / "memory.md")
        contexto = agent.carregar_contexto()
        assert contexto.index("Identidade X") < contexto.index("# Memória") < contexto.index("Fato Y")

    def test_agent_md_do_repositorio_exige_nao_inventar(self):
        texto = agent.AGENT_MD.read_text(encoding="utf-8").lower()
        assert "não invente" in texto
        assert "português" in texto


@pytest.mark.unitario
class TestFerramentasRobustas:
    def test_argumento_extra_vira_erro_para_o_modelo(self):
        saida = json.loads(agent.executar_ferramenta("somar", {"a": 1, "b": 2, "c": 3}))
        assert "erro" in saida

    def test_texto_no_lugar_de_numero_nao_derruba_o_agente(self):
        saida = agent.executar_ferramenta("somar", {"a": "dois", "b": 3})
        assert isinstance(saida, str)
        assert "erro" in json.loads(saida) or "resultado" in json.loads(saida)

    def test_soma_de_valores_grandes_e_exata(self):
        saida = json.loads(agent.executar_ferramenta("somar", {"a": 123456789, "b": 987654321}))
        assert saida["resultado"] == 1111111110
