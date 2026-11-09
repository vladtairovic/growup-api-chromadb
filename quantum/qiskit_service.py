import re

from qiskit import QuantumCircuit, transpile, qasm2
from qiskit.quantum_info import Operator
from qiskit.transpiler import CouplingMap
from qiskit.exceptions import QiskitError

MAX_CARACTERES_QASM = 10_000
LIM_MAX_EQUIV = 10
MAX_QUBITS_QASM = 32
MAX_BITS_CLASSICOS_QASM = 32
MAX_OPERACOES_QASM = 500

# ==== Funções ====
def validar_circuito(circuito):
    if not isinstance(circuito, QuantumCircuit):
        raise TypeError(
            "O circuito deve ser um QuantumCircuit."
        )

def carregar_circuito_qasm(texto_qasm: str):
    """
    Converte texto OpenQASM 2 em QuantumCircuit,
    aplicando validações básicas de entrada.
    """

    if not isinstance(texto_qasm, str):
        raise TypeError("O OpenQASM deve ser uma string.")

    if not texto_qasm.strip():
        raise ValueError("O texto OpenQASM não pode estar vazio.")

    if len(texto_qasm) > MAX_CARACTERES_QASM:
        raise ValueError(
            "O texto OpenQASM ultrapassa o tamanho permitido."
        )

    # Remover comentários antes de analisar declarações
    texto_limpo = re.sub(
        r"//[^\n]*|/\*.*?\*/",
        " ",
        texto_qasm,
        flags=re.DOTALL
    )

    # Identificar declarações qreg e creg
    declaracoes = re.findall(
        r"\b(qreg|creg)\s+[A-Za-z_][A-Za-z0-9_]*\s*\[\s*(\d+)\s*\]\s*;",
        texto_limpo
    )

    total_qubits = sum(
        int(tamanho)
        for tipo, tamanho in declaracoes
        if tipo == "qreg"
    )

    total_bits = sum(
        int(tamanho)
        for tipo, tamanho in declaracoes
        if tipo == "creg"
    )

    if total_qubits > MAX_QUBITS_QASM:
        raise ValueError(
            f"O circuito ultrapassa o limite de "
            f"{MAX_QUBITS_QASM} qubits."
        )

    if total_bits > MAX_BITS_CLASSICOS_QASM:
        raise ValueError(
            f"O circuito ultrapassa o limite de "
            f"{MAX_BITS_CLASSICOS_QASM} bits clássicos."
        )

    try:
        circuito = qasm2.loads(
            texto_qasm,
            include_path=()
        )

    except qasm2.QASM2Error as erro:
        raise ValueError(
            "Não foi possível interpretar o OpenQASM 2."
        ) from erro

    # Conferência do circuito reconstruído
    if circuito.num_qubits > MAX_QUBITS_QASM:
        raise ValueError("Limite de qubits excedido.")

    if circuito.num_clbits > MAX_BITS_CLASSICOS_QASM:
        raise ValueError("Limite de bits clássicos excedido.")

    if circuito.size() > MAX_OPERACOES_QASM:
        raise ValueError(
            f"O circuito ultrapassa o limite de "
            f"{MAX_OPERACOES_QASM} operações."
        )

    return circuito

def exportar_circuito_qasm(circuito: QuantumCircuit):
    """
    Converte um QuantumCircuit em texto OpenQASM 2.
    """
    validar_circuito(circuito)

    try:
        return qasm2.dumps(circuito)

    except qasm2.QASM2Error as erro:
        raise ValueError(
            "Não foi possível exportar o circuito para OpenQASM 2."
        ) from erro


def processar_circuito_qasm(texto_qasm: str, nivel_otimizacao: int = 3):
    """
    Recebe OpenQASM 2, otimiza o circuito e retorna
    resultados utilizáveis pela API.
    """
    original = carregar_circuito_qasm(texto_qasm)

    otimizado = otimizar_circuito(
        original,
        nivel_otimizacao
    )

    resultado = avaliar_proposta_ia(
        original,
        otimizado
    )

    resultado["circuito_otimizado_qasm"] = (
        exportar_circuito_qasm(otimizado)
    )

    return resultado


def obter_metricas(circuito: QuantumCircuit):
    """
    Analisa um circuito quântico e retorna
    suas principais métricas.
    """
    validar_circuito(circuito)

    metricas = {
        "qubits": circuito.num_qubits,
        "total_operacoes": circuito.size(),
        "profundidade": circuito.depth(),
        "tipos_operacoes": dict(circuito.count_ops())
    }
    return metricas

def otimizar_circuito(circuito:QuantumCircuit, nivel_otimizacao:int=3):
    '''
    Recebe um circuito quântico junto com nível
    de otimização, sendo o padrão 3, e faz o processo
    com transpile.
    '''
    validar_circuito(circuito)

    if nivel_otimizacao not in (0, 1, 2, 3):
        raise ValueError("Nível de otimização deve ser 0, 1, 2 ou 3.")

    circuito_otimizado = transpile(
    circuito,
    optimization_level=nivel_otimizacao,
    seed_transpiler=42
    )
    return circuito_otimizado

def otimizar_para_hardware(circuito: QuantumCircuit, conectividade: CouplingMap, layout_inicial=None, nivel_otimizacao:int=0, portas_nativas: list[str] | None = None):
    """
    Adapta um circuito quântico às restrições
    de conectividade e portas nativas do hardware.
    """
    validar_circuito(circuito)

    if not isinstance(conectividade, CouplingMap):
        raise TypeError(
            "O parâmetro 'conectividade' deve ser um CouplingMap."
        )

    if nivel_otimizacao not in (0, 1, 2, 3):
        raise ValueError("Nível de otimização deve ser 0, 1, 2 ou 3.")

    otimizado = transpile(
        circuito,
        coupling_map=conectividade,
        basis_gates=portas_nativas,
        initial_layout=layout_inicial,
        layout_method = "sabre" if layout_inicial is None else None,
        routing_method= "basic",
        optimization_level=nivel_otimizacao,
        seed_transpiler=42
    )
    return otimizado

def verificar_equivalencia(original: QuantumCircuit, otimizado: QuantumCircuit, limite_qubits: int = LIM_MAX_EQUIV):
    """
    Verifica equivalência de circuitos unitários,
    considerando os metadados de layout.

    Gera ValueError caso a comparação não
    possa ser realizada.
    """
    validar_circuito(original)
    validar_circuito(otimizado)

    if type(limite_qubits) is not int or limite_qubits < 1:
            raise ValueError(
                "O limite de qubits deve ser um inteiro positivo."
            )

    if limite_qubits > LIM_MAX_EQUIV:
        raise ValueError(
            f"O limite de qubits não pode ultrapassar "
            f"{LIM_MAX_EQUIV}."
        )

    if original.num_qubits != otimizado.num_qubits:
        return False

    if original.num_qubits > limite_qubits:
        raise ValueError(
            f"O circuito possui {original.num_qubits} qubits, "
            f"acima do limite permitido de {limite_qubits}."
        )

    try:
        operador_original = Operator.from_circuit(original)
        operador_otimizado = Operator.from_circuit(otimizado)

        return bool(
            operador_original.equiv(operador_otimizado)
        )

    except QiskitError as erro:
        raise ValueError(
            "Não foi possível verificar equivalência pelo método de operadores unitários."
        ) from erro


def comparar_niveis(circuito: QuantumCircuit):
    """
    Compara o circuito original com suas versões
    otimizadas em diferentes níveis de otimização.
    """
    resultados = {}
    nivel = 0

    while nivel <= 3:
        otimizado = otimizar_circuito(circuito, nivel)

        motivo = None

        try:
            equivalente = verificar_equivalencia(
                circuito, otimizado
            )

            if equivalente:
                status = "equivalente"
            else:
                status = "nao_equivalente"

        except ValueError as erro:
            equivalente = None
            status = "nao_verificado"
            motivo = str(erro)

        resultados[nivel] = {
            "metricas": obter_metricas(otimizado),
            "equivalente": equivalente,
            "status_verificacao": status,
            "motivo": motivo
        }

        nivel += 1

    return resultados

def analisar_adaptacao_hardware(original: QuantumCircuit, adaptado: QuantumCircuit, portas_nativas: list[str] | None = None):
    """
    Compara um circuito original com sua versão
    adaptada ao hardware.
    """

    # Obter métricas
    metricas_originais = obter_metricas(original)
    metricas_adaptadas = obter_metricas(adaptado)

    # Calcular diferenças
    diferenca_operacoes = (
        metricas_adaptadas["total_operacoes"]
        - metricas_originais["total_operacoes"]
    )

    diferenca_profundidade = (
        metricas_adaptadas["profundidade"]
        - metricas_originais["profundidade"]
    )

    # Verificar equivalência
    motivo = None

    try:
        equivalente = verificar_equivalencia(
            original, adaptado
        )

        if equivalente:
            status = "equivalente"
        else:
            status = "nao_equivalente"

    except ValueError as erro:
        equivalente = None
        status = "nao_verificado"
        motivo = str(erro)

    # Verificar portas nativas
    compativel_portas = None

    if portas_nativas is not None:
        compativel_portas = set(adaptado.count_ops()).issubset(set(portas_nativas))

    resultados = {
        "original": metricas_originais,
        "adaptado": metricas_adaptadas,
        "diferenca_operacoes": diferenca_operacoes,
        "diferenca_profundidade": diferenca_profundidade,
        "equivalente": equivalente,
        "status_verificacao": status,
        "motivo": motivo,
        "somente_portas_permitidas": compativel_portas
    }

    return resultados

def avaliar_proposta_ia(original: QuantumCircuit, proposta: QuantumCircuit):
    """
    Avalia uma proposta de otimização quântica,
    considerando métricas e equivalência.
    """

    metricas_original = obter_metricas(original)
    metricas_proposta = obter_metricas(proposta)

    diferenca_operacoes = (
        metricas_proposta["total_operacoes"]
        - metricas_original["total_operacoes"]
    )

    diferenca_profundidade = (
        metricas_proposta["profundidade"]
        - metricas_original["profundidade"]
    )

    # Tentar verificar equivalência
    motivo = None

    try:
        equivalente = verificar_equivalencia(
            original, proposta
        )

        if equivalente:
            status = "equivalente"
        else:
            status = "nao_equivalente"

    except ValueError as erro:
        equivalente = None
        status = "nao_verificado"
        motivo = str(erro)

    # Avaliar reduções apenas se houve verificação
    if equivalente is None:
        reduziu_operacoes = None
        reduziu_profundidade = None
    else:
        reduziu_operacoes = (
            equivalente and diferenca_operacoes < 0
        )

        reduziu_profundidade = (
            equivalente and diferenca_profundidade < 0
        )

    resultados = {
        "original": metricas_original,
        "proposta": metricas_proposta,
        "equivalente": equivalente,
        "status_verificacao": status,
        "motivo": motivo,
        "diferenca_operacoes": diferenca_operacoes,
        "diferenca_profundidade": diferenca_profundidade,
        "reduziu_operacoes": reduziu_operacoes,
        "reduziu_profundidade": reduziu_profundidade
    }

    return resultados
