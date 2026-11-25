import unittest

from tabela_hash import TabelaHash


class TestTabelaHash(unittest.TestCase):
    def setUp(self):
        self.tabela = TabelaHash(capacidade=7)

    def test_inserir_e_buscar(self):
        self.tabela.inserir(101, "Ana")
        self.assertEqual(self.tabela.buscar(101), "Ana")
        self.assertIsNone(self.tabela.buscar(999))

    def test_colisao_localiza_os_dois(self):
        self.tabela.inserir(101, "Ana")
        self.tabela.inserir(108, "Bruno")
        self.assertEqual(self.tabela.colisoes(), 1)
        self.assertEqual(self.tabela.buscar(101), "Ana")
        self.assertEqual(self.tabela.buscar(108), "Bruno")

    def test_id_duplicado(self):
        self.tabela.inserir(101, "Ana")
        with self.assertRaises(KeyError):
            self.tabela.inserir(101, "Outra")
        self.assertEqual(len(self.tabela), 1)

    def test_remover_inicio_e_meio_da_lista(self):
        for id_ in (3, 10, 17):
            self.tabela.inserir(id_, f"P{id_}")
        self.assertEqual(self.tabela.remover(10), "P10")
        self.assertEqual(self.tabela.remover(17), "P17")
        self.assertEqual(self.tabela.buscar(3), "P3")
        self.assertEqual(len(self.tabela), 1)
        self.tabela.validar()

    def test_remover_inexistente(self):
        with self.assertRaises(KeyError):
            self.tabela.remover(42)

    def test_atualizar(self):
        self.tabela.inserir(101, "Ana")
        self.tabela.atualizar(101, "Ana Paula")
        self.assertEqual(self.tabela.buscar(101), "Ana Paula")
        with self.assertRaises(KeyError):
            self.tabela.atualizar(5, "x")

    def test_redimensiona_e_mantem_tudo(self):
        ids = list(range(1000, 1050))
        for id_ in ids:
            self.tabela.inserir(id_, id_)
        self.assertGreater(self.tabela.capacidade(), 7)
        self.assertLessEqual(self.tabela.fator_carga(), TabelaHash.CARGA_MAXIMA)
        for id_ in ids:
            self.assertEqual(self.tabela.buscar(id_), id_)
        self.assertEqual(sorted(self.tabela.chaves()), ids)
        self.tabela.validar()

    def test_chave_invalida(self):
        with self.assertRaises(TypeError):
            self.tabela.inserir("101", "Ana")


if __name__ == "__main__":
    unittest.main()
