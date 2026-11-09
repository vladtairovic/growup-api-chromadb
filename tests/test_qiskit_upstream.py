import unittest

import json

from qiskit import QuantumCircuit, qasm2
from qiskit.transpiler import CouplingMap

from quantum.qiskit_service import (obter_metricas, otimizar_circuito, verificar_equivalencia, comparar_niveis, otimizar_para_hardware, analisar_adaptacao_hardware, avaliar_proposta_ia, carregar_circuito_qasm, exportar_circuito_qasm, processar_circuito_qasm)

class TestQiskitService(unittest.TestCase):

    def test_carregar_circuito_qasm(self):
        original = QuantumCircuit(2)
        original.h(0)
        original.cx(0, 1)

        texto = qasm2.dumps(original)

        reconstruido = carregar_circuito_qasm(texto)

        self.assertTrue(
            verificar_equivalencia(original, reconstruido)
        )

        with self.assertRaises(TypeError):
            carregar_circuito_qasm(None)

        with self.assertRaises(ValueError):
            carregar_circuito_qasm("texto invalido")

        with self.assertRaises(ValueError):
            carregar_circuito_qasm("X" * 10001)

        qasm_muitos_qubits = (
            "OPENQASM 2.0;\n"
            "qreg q[33];\n"
        )

        with self.assertRaisesRegex(ValueError, "qubits"):
            carregar_circuito_qasm(qasm_muitos_qubits)

        qasm_muitas_operacoes = (
            "OPENQASM 2.0;\n"
            'include "qelib1.inc";\n'
            "qreg q[1];\n"
            + "x q[0];\n" * 501
        )

        with self.assertRaisesRegex(ValueError, "operações"):
            carregar_circuito_qasm(qasm_muitas_operacoes)


    def test_processar_circuito_qasm(self):
        circuito = QuantumCircuit(2)
        circuito.x(0)
        circuito.x(0)
        circuito.h(0)
        circuito.cx(0, 1)

        texto = qasm2.dumps(circuito)

        resultado = processar_circuito_qasm(texto)

        reconstruido = carregar_circuito_qasm(
            resultado["circuito_otimizado_qasm"]
        )

        self.assertTrue(
            verificar_equivalencia(circuito, reconstruido)
        )

        self.assertEqual(
            resultado["status_verificacao"],
            "equivalente"
        )

        json.dumps(resultado, ensure_ascii=False)


    def test_metricas(self):
        circuito = QuantumCircuit(2)
        circuito.h(0)
        circuito.cx(0, 1)

        metricas = obter_metricas(circuito)

        self.assertEqual(metricas["qubits"], 2)
        self.assertEqual(metricas["total_operacoes"], 2)
        self.assertEqual(metricas["profundidade"], 2)

    def test_otimizacao_basica(self):
        circuito = QuantumCircuit(1)
        circuito.x(0)
        circuito.x(0)

        otimizado = otimizar_circuito(circuito)

        self.assertTrue(
            verificar_equivalencia(circuito, otimizado)
        )

    def test_niveis_otimizacao(self):
        circuito = QuantumCircuit(1)
        circuito.h(0)
        circuito.h(0)

        resultados = comparar_niveis(circuito)

        self.assertEqual(set(resultados), {0, 1, 2, 3})

        for resultado in resultados.values():
            self.assertTrue(resultado["equivalente"])

    def test_nivel_invalido(self):
        circuito = QuantumCircuit(1)

        with self.assertRaises(ValueError):
            otimizar_circuito(circuito, 5)

    def test_equivalencia_incorreta(self):
        original = QuantumCircuit(1)
        original.h(0)

        diferente = QuantumCircuit(1)
        diferente.x(0)

        self.assertFalse(
            verificar_equivalencia(original, diferente)
        )

    def test_otimizacao_hardware(self):
        circuito = QuantumCircuit(3)
        circuito.h(0)
        circuito.cx(0, 2)
        circuito.cx(0, 1)

        conectividade = CouplingMap.from_line(3)
        portas = ["rz", "sx", "x", "cx"]

        adaptado = otimizar_para_hardware(
            circuito,
            conectividade,
            portas_nativas=portas
        )

        self.assertTrue(
            verificar_equivalencia(circuito, adaptado)
        )

        self.assertTrue(
            set(adaptado.count_ops()).issubset(set(portas))
        )

    def test_analise_hardware(self):
        original = QuantumCircuit(1)
        original.h(0)

        adaptado = QuantumCircuit(1)
        adaptado.h(0)

        resultado = analisar_adaptacao_hardware(
            original, adaptado
        )

        self.assertEqual(
            resultado["status_verificacao"],
            "equivalente"
        )

    def test_proposta_ia(self):
        original = QuantumCircuit(1)
        original.x(0)
        original.x(0)

        proposta = QuantumCircuit(1)

        resultado = avaliar_proposta_ia(
            original, proposta
        )

        self.assertTrue(resultado["equivalente"])
        self.assertTrue(resultado["reduziu_operacoes"])


    def test_proposta_ia_incorreta(self):
        original = QuantumCircuit(2)
        original.h(0)
        original.cx(0, 1)

        proposta = QuantumCircuit(2)
        proposta.h(0)

        resultado = avaliar_proposta_ia(
            original,
            proposta
        )

        self.assertEqual(
            resultado["diferenca_operacoes"],
            -1
        )

        self.assertFalse(resultado["equivalente"])

        self.assertEqual(
            resultado["status_verificacao"],
            "nao_equivalente"
        )

        self.assertFalse(resultado["reduziu_operacoes"])
        self.assertFalse(resultado["reduziu_profundidade"])


    def test_medicao_nao_verificada(self):
        original = QuantumCircuit(1)
        original.h(0)

        proposta = QuantumCircuit(1, 1)
        proposta.h(0)
        proposta.measure(0, 0)

        resultado = avaliar_proposta_ia(
            original, proposta
        )

        self.assertEqual(
            resultado["status_verificacao"],
            "nao_verificado"
        )

        self.assertIsNone(resultado["equivalente"])


    def test_equivalencia_com_layout_diferente(self):
        circuito = QuantumCircuit(3)
        circuito.h(0)
        circuito.cx(0, 1)
        circuito.cx(0, 2)

        conectividade = CouplingMap.from_line(3)

        layout_inicial = [1, 0, 2]

        adaptado = otimizar_para_hardware(
            circuito,
            conectividade,
            layout_inicial=layout_inicial,
            portas_nativas=["rz", "sx", "x", "cx"]
        )

        self.assertEqual(
            adaptado.layout.initial_index_layout(),
            layout_inicial
        )

        self.assertTrue(
            verificar_equivalencia(circuito, adaptado)
        )

    def test_nivel_invalido_hardware(self):
        circuito = QuantumCircuit(3)

        conectividade = CouplingMap.from_line(3)

        with self.assertRaises(ValueError):
            otimizar_para_hardware(
                circuito,
                conectividade,
                nivel_otimizacao=5
            )


    def test_analise_hardware_nao_verificada(self):
        original = QuantumCircuit(1)
        original.h(0)

        adaptado = QuantumCircuit(1, 1)
        adaptado.h(0)
        adaptado.measure(0, 0)

        resultado = analisar_adaptacao_hardware(
            original,
            adaptado
        )

        self.assertEqual(
            resultado["status_verificacao"],
            "nao_verificado"
        )

        self.assertIsNone(
            resultado["equivalente"]
        )

        self.assertIsNotNone(
            resultado["motivo"]
        )


    def test_portas_nao_permitidas(self):
        original = QuantumCircuit(1)
        original.h(0)

        adaptado = QuantumCircuit(1)
        adaptado.h(0)

        portas_nativas = ["rz", "sx", "x", "cx"]

        resultado = analisar_adaptacao_hardware(
            original,
            adaptado,
            portas_nativas
        )

        self.assertTrue(resultado["equivalente"])

        self.assertFalse(
            resultado["somente_portas_permitidas"]
        )

    def test_comparar_niveis_nao_verificado(self):
        circuito = QuantumCircuit(1, 1)
        circuito.h(0)
        circuito.measure(0, 0)

        resultados = comparar_niveis(circuito)

        self.assertEqual(
            set(resultados),
            {0, 1, 2, 3}
        )

        for dados in resultados.values():
            self.assertEqual(
                dados["status_verificacao"],
                "nao_verificado"
            )

            self.assertIsNone(
                dados["equivalente"]
            )

            self.assertIsNotNone(
                dados["motivo"]
            )


    def test_circuito_entrada_invalida(self):
        entradas_invalidas = [
            "circuito invalido",
            None,
            123
        ]

        circuito_valido = QuantumCircuit(1)

        conectividade_valida = CouplingMap.from_line(2)

        for entrada in entradas_invalidas:
            with self.subTest(entrada=entrada):

                with self.assertRaises(TypeError):
                    obter_metricas(entrada)

                with self.assertRaises(TypeError):
                    otimizar_circuito(entrada)

                with self.assertRaises(TypeError):
                    verificar_equivalencia(
                        entrada, circuito_valido
                    )
                with self.assertRaises(TypeError):
                    verificar_equivalencia(
                        circuito_valido, entrada
                    )
                with self.assertRaises(TypeError):
                    otimizar_para_hardware(
                        entrada,
                        conectividade_valida
                    )

    def test_conectividade_invalida(self):
        circuito = QuantumCircuit(2)

        entradas_invalidas = [
            None,
            "conectividade invalida",
            123
        ]

        for entrada in entradas_invalidas:
            with self.subTest(entrada=entrada):
                with self.assertRaises(TypeError):
                    otimizar_para_hardware(
                        circuito,
                        entrada
                    )


    def test_limite_qubits_equivalencia(self):

        circuito_grande = QuantumCircuit(11)

        with self.assertRaises(ValueError):
            verificar_equivalencia(
                circuito_grande,
                circuito_grande
            )

        circuito_pequeno = QuantumCircuit(2)

        with self.assertRaises(ValueError):
            verificar_equivalencia(
                circuito_pequeno,
                circuito_pequeno,
                limite_qubits=1
            )

        self.assertTrue(
            verificar_equivalencia(
                circuito_pequeno,
                circuito_pequeno,
                limite_qubits=2
            )
        )

        limites_invalidos = [0, -1, True,"10", 11, 30]

        for limite in limites_invalidos:
            with self.subTest(limite=limite):
                with self.assertRaises(ValueError):
                    verificar_equivalencia(
                        circuito_pequeno,
                        circuito_pequeno,
                        limite_qubits=limite
                    )

if __name__ == "__main__":
    unittest.main()
