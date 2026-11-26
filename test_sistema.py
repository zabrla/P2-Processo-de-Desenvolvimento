import random
import unittest

from sistema import SIGAE, ErroSIGAE, AGUARDANDO, EM_ATENDIMENTO, CONCLUIDO, CANCELADO


class TestSIGAE(unittest.TestCase):
    def setUp(self):
        self.s = SIGAE(consultorios=2)
        self.s.carregar(SIGAE.CENARIO_PADRAO)

    def test_cadastro_entra_nas_tres_estruturas(self):
        ficha = self.s.cadastrar("Fernanda Alves", "08:25", 3)
        self.assertEqual(ficha.id, 1005)
        self.assertTrue(self.s.espera.contem(1005))
        self.assertIn(1005, self.s.heap)
        self.assertIsNotNone(self.s.arvore.buscar("08:25", 1005))
        self.s.validar()

    def test_id_repetido_e_dados_invalidos(self):
        with self.assertRaises(ErroSIGAE):
            self.s.cadastrar("Outro", "09:00", 2, 1003)
        with self.assertRaises(ErroSIGAE):
            self.s.cadastrar("Outro", "9h", 2)
        with self.assertRaises(ErroSIGAE):
            self.s.cadastrar("Outro", "09:00", 7)
        with self.assertRaises(ErroSIGAE):
            self.s.cadastrar(" ", "09:00", 2)
        self.assertEqual(self.s.aguardando(), 5)
        self.s.validar()

    def test_rollback_quando_uma_estrutura_falha(self):
        def falha(_):
            raise RuntimeError("falha simulada no heap")
        self.s.heap.inserir = falha
        with self.assertRaises(ErroSIGAE):
            self.s.cadastrar("Fernanda Alves", "08:25", 3)
        del self.s.heap.inserir
        self.assertFalse(self.s.espera.contem(1005))
        self.assertIsNone(self.s.arvore.buscar("08:25", 1005))
        self.s.validar()

    def test_a_colisao_localiza_os_dois(self):
        self.s.carregar(SIGAE.CENARIO_COLISAO)
        self.assertEqual(self.s.espera.colisoes(), 4)
        for id_paciente in (1000, 1011, 1022, 1033, 1044):
            self.assertEqual(self.s.localizar(id_paciente).id, id_paciente)
        self.s.validar()

    def test_b_reclassificar_muda_a_raiz(self):
        self.assertEqual(self.s.proximo_da_fila().id, 1003)
        self.s.reclassificar(1002, 1)  # 1002 chegou antes de 1003 e empata em P1
        self.assertEqual(self.s.proximo_da_fila().id, 1002)
        self.s.reclassificar(1002, 5)
        self.assertEqual(self.s.proximo_da_fila().id, 1003)
        self.s.validar()

    def test_c_dois_medicos(self):
        a = self.s.chamar_proximo()
        b = self.s.chamar_proximo()
        self.assertEqual((a.id, a.consultorio), (1003, 1))
        self.assertEqual((b.id, b.consultorio), (1001, 2))
        self.assertEqual(self.s.aguardando(), 3)
        with self.assertRaises(ErroSIGAE):
            self.s.chamar_proximo()
        with self.assertRaises(ErroSIGAE):
            self.s.concluir()  # dois ocupados: precisa dizer qual
        self.assertEqual(self.s.concluir(2).status, CONCLUIDO)
        c = self.s.chamar_proximo()
        self.assertEqual(c.consultorio, 2)
        self.s.validar()

    def test_c_cancelar_e_estados(self):
        self.s.cancelar(1002)
        self.assertEqual(self.s.localizar(1002).status, CANCELADO)
        self.assertIsNone(self.s.arvore.buscar("08:10", 1002))
        with self.assertRaises(ErroSIGAE):
            self.s.cancelar(1002)
        with self.assertRaises(ErroSIGAE):
            self.s.reclassificar(1002, 1)
        chamado = self.s.chamar_proximo()
        self.assertEqual(self.s.localizar(chamado.id).status, EM_ATENDIMENTO)
        with self.assertRaises(ErroSIGAE):
            self.s.cancelar(chamado.id)
        self.s.validar()

    def test_lista_por_chegada(self):
        self.s.cadastrar("Gabriel", "07:50", 2)
        ordem = [f.id for f in self.s.lista_por_chegada()]
        self.assertEqual(ordem, [1005, 1000, 1001, 1002, 1003, 1004])

    def test_operacoes_aleatorias_mantem_consistencia(self):
        aleatorio = random.Random(42)
        self.s.limpar()
        for _ in range(1500):
            acao = aleatorio.random()
            aguardando = self.s.espera.chaves()
            try:
                if acao < 0.4 or not aguardando:
                    hora = f"{aleatorio.randint(0, 23):02d}:{aleatorio.randint(0, 59):02d}"
                    self.s.cadastrar("Paciente", hora, aleatorio.randint(1, 5))
                elif acao < 0.55:
                    self.s.reclassificar(aleatorio.choice(aguardando), aleatorio.randint(1, 5))
                elif acao < 0.7:
                    self.s.cancelar(aleatorio.choice(aguardando))
                elif acao < 0.85:
                    self.s.chamar_proximo()
                else:
                    ocupados = [i + 1 for i, f in enumerate(self.s.consultorios) if f]
                    if ocupados:
                        self.s.concluir(aleatorio.choice(ocupados))
            except ErroSIGAE:
                pass
            self.s.validar()
            proximo = self.s.proximo_da_fila()
            if proximo:
                menor = min(self.s.fichas.buscar(i).paciente.chave() for i in self.s.espera.chaves())
                self.assertEqual(proximo.paciente.chave(), menor)


if __name__ == "__main__":
    unittest.main()
