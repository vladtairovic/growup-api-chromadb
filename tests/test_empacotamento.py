from pathlib import Path
import json

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_tem_dois_servicos_e_banco_persistente_interno():
    config = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    assert set(config["services"]) == {"api", "chroma"}
    assert config["services"]["chroma"]["image"] == "chromadb/chroma:1.5.9"
    assert "ports" not in config["services"]["chroma"]
    assert "chroma_data:/data" in config["services"]["chroma"]["volumes"]
    assert config["networks"]["banco"]["internal"] is True
    assert config["services"]["api"]["environment"]["CHROMA_HOST"] == "chroma"


def test_snapshot_tem_origem_e_secoes_para_reconstrucao():
    docs = json.loads((ROOT / "documentos" / "base_documental.json").read_text(encoding="utf-8"))
    assert len(docs) == 3
    for doc in docs:
        assert doc["document_id"] and doc["secoes"]
        assert doc["fonte"].startswith("https://quantum.cloud.ibm.com/")


def test_codigo_publicado_nao_abre_banco_local():
    for path in (ROOT / "rag").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "PersistentClient(" not in source
        assert "C:/Users/" not in source and "C:\\Users\\" not in source
