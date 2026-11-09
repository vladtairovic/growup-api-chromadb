"""Limita concorrência e encerra o processo Qiskit quando excede o prazo."""
import asyncio
import json
import os
import sys
from fastapi import APIRouter, HTTPException
from pydantic import Field
from contratos import Modelo

router = APIRouter()
_slots = asyncio.Semaphore(1)

class Circuito(Modelo):
    qasm: str = Field(min_length=1, max_length=10000)
    optimization_level: int = Field(default=3, ge=0, le=3, strict=True)

class ResultadoQiskit(Modelo):
    original: dict
    proposta: dict
    equivalente: bool | None
    status_verificacao: str
    motivo: str | None
    diferenca_operacoes: int
    diferenca_profundidade: int
    reduziu_operacoes: bool | None
    reduziu_profundidade: bool | None
    circuito_otimizado_qasm: str

@router.post("/qiskit/optimize", response_model=ResultadoQiskit)
async def otimizar(entrada: Circuito):
    """Transpila OpenQASM 2 e verifica equivalência quando possível; sem LLM."""
    async def executar():
        async with _slots:
            processo = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "quantum.worker",
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL)
            try:
                saida, _ = await processo.communicate(entrada.model_dump_json().encode())
            finally:
                if processo.returncode is None:
                    processo.kill()
                    await processo.wait()
            if processo.returncode != 0:
                raise HTTPException(503)
            resultado = json.loads(saida)
            if resultado.get("invalid"):
                raise HTTPException(422)
            return resultado["result"]
    return await asyncio.wait_for(executar(), timeout=float(os.getenv("QISKIT_TIMEOUT_SECONDS", "30")))
