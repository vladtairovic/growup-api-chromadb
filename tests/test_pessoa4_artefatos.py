"""Testes locais de contrato para prompts e conjunto de avaliação (stdlib)."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ArtefatosPessoa4Test(unittest.TestCase):
    def test_prompt_principal_exige_fundamentacao_e_limites(self):
        prompt = (ROOT / "prompts" / "system_prompt_v1.md").read_text(encoding="utf-8").lower()
        for requisito in ("contexto recuperado", "não invente", "evidências suficientes", "fontes", "limitações"):
            self.assertIn(requisito, prompt)

    def test_prompt_otimizacao_nao_garante_melhoria_sem_evidencia(self):
        prompt = (ROOT / "prompts" / "optimization_prompt_v1.md").read_text(encoding="utf-8").lower()
        self.assertIn("não afirme", prompt)
        self.assertIn("métricas", prompt)
        self.assertIn("verificações necessárias", prompt)

    def test_casos_de_avaliacao_tem_campos_obrigatorios(self):
        casos = json.loads((ROOT / "tests" / "casos_avaliacao.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(casos), 6)
        ids = [caso["id"] for caso in casos]
        self.assertEqual(len(ids), len(set(ids)), "IDs dos casos devem ser únicos")
        for caso in casos:
            for campo in ("id", "categoria", "pergunta", "resultado_esperado", "falha_critica", "status"):
                self.assertTrue(caso.get(campo), f"Campo {campo} ausente em {caso.get('id')}")

    def test_prompts_exigem_saida_em_portugues_do_brasil(self):
        principal = (ROOT / "prompts" / "system_prompt_v1.md").read_text(encoding="utf-8").lower()
        otimizacao = (ROOT / "prompts" / "optimization_prompt_v1.md").read_text(encoding="utf-8").lower()
        self.assertIn("português do brasil", principal)
        self.assertIn("português do brasil", otimizacao)
        self.assertIn("fontes consultadas", principal)
        self.assertIn("limitações e verificações necessárias", principal)

    def test_documentacao_define_contrato_de_api_em_portugues(self):
        doc = (ROOT / "docs" / "PESSOA_4_DOCUMENTACAO.md").read_text(encoding="utf-8").lower()
        for campo in ('"resposta"', '"fontes"', '"avisos"', '"estado"'):
            self.assertIn(campo, doc)
        self.assertIn("não implementa o endpoint da api", doc)

    def test_conjunto_cobre_fora_da_base_e_contexto_insuficiente(self):
        casos = json.loads((ROOT / "tests" / "casos_avaliacao.json").read_text(encoding="utf-8"))
        categorias = {caso["categoria"] for caso in casos}
        self.assertIn("fora_da_base", categorias)
        self.assertIn("contexto_insuficiente", categorias)
        self.assertIn("versao", categorias)

if __name__ == "__main__":
    unittest.main()
