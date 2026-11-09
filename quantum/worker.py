"""Processo isolado: somente OpenQASM, nunca eval/exec de Python recebido."""
import json
import sys
from .qiskit_service import processar_circuito_qasm

def main():
    entrada = json.load(sys.stdin)
    try:
        resultado = processar_circuito_qasm(entrada["qasm"], entrada["optimization_level"])
        print(json.dumps({"result": resultado}))
    except (ValueError, TypeError):
        print(json.dumps({"invalid": True}))

if __name__ == "__main__":
    main()
