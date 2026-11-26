"""Persistência em SQLite para a interface web."""

import os
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from sigae.modelos.paciente import Paciente
from sigae.sistema import (
    AGUARDANDO,
    CANCELADO,
    CONCLUIDO,
    EM_ATENDIMENTO,
    ErroSIGAE,
    Ficha,
    SIGAE,
    horario_em_minutos,
)

BANCO_PADRAO = Path(__file__).resolve().parent.parent / "sigae.db"
ID_MAXIMO = 2**63 - 1


class BancoSIGAE:
    def __init__(self, caminho=None):
        self.caminho = caminho or os.environ.get("SIGAE_DB_PATH") or BANCO_PADRAO
        with self._conectar() as conexao:
            versao = conexao.execute("PRAGMA user_version").fetchone()[0]
        if versao == 0:
            with self._conectar(escrita=True) as conexao:
                if conexao.execute("PRAGMA user_version").fetchone()[0] == 0:
                    self._migrar(conexao)
        elif versao != 1:
            raise ErroSIGAE(f"Versão de banco incompatível: {versao}.")

    @staticmethod
    def _migrar(conexao):
        legado = conexao.execute(
            "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'fichas'"
        ).fetchone()
        if legado:
            conexao.execute("ALTER TABLE fichas RENAME TO fichas_legado")

        conexao.execute("""
            CREATE TABLE fichas (
                id INTEGER PRIMARY KEY CHECK (id > 0),
                nome TEXT NOT NULL CHECK (length(nome) BETWEEN 2 AND 90),
                horario TEXT NOT NULL,
                prioridade INTEGER NOT NULL CHECK (prioridade IN (1, 2)),
                status TEXT NOT NULL,
                consultorio INTEGER CHECK (consultorio IN (1, 2)),
                ordem_encerramento INTEGER UNIQUE CHECK (ordem_encerramento > 0),
                CHECK (
                    (status = 'Aguardando' AND consultorio IS NULL AND ordem_encerramento IS NULL)
                    OR (status = 'Em atendimento' AND consultorio IS NOT NULL AND ordem_encerramento IS NULL)
                    OR (status = 'Concluído' AND consultorio IS NOT NULL AND ordem_encerramento IS NOT NULL)
                    OR (status = 'Cancelado' AND consultorio IS NULL AND ordem_encerramento IS NOT NULL)
                )
            )
        """)

        if legado:
            conexao.execute("""
                INSERT INTO fichas
                    (id, nome, horario, prioridade, status, consultorio, ordem_encerramento)
                SELECT id, nome, horario, CASE WHEN prioridade <= 3 THEN 1 ELSE 2 END,
                       status, consultorio, ordem_encerramento
                FROM fichas_legado
            """)
            conexao.execute("DROP TABLE fichas_legado")

        conexao.execute("""
            CREATE UNIQUE INDEX consultorio_ocupado
            ON fichas(consultorio) WHERE status = 'Em atendimento'
        """)
        conexao.execute("PRAGMA user_version = 1")

    @contextmanager
    def _conectar(self, escrita=False):
        with closing(sqlite3.connect(self.caminho, timeout=10)) as conexao, conexao:
            conexao.row_factory = sqlite3.Row
            if escrita:
                conexao.execute("BEGIN IMMEDIATE")
            yield conexao

    def carregar(self):
        with self._conectar() as conexao:
            return self._restaurar(conexao)

    @staticmethod
    def _restaurar(conexao):
        sistema = SIGAE()
        linhas = conexao.execute("""
            SELECT id, nome, horario, prioridade, status, consultorio
            FROM fichas ORDER BY ordem_encerramento, id
        """)
        for linha in linhas:
            id_paciente = linha["id"]
            nome, horario, prioridade = linha["nome"], linha["horario"], linha["prioridade"]
            status, consultorio = linha["status"], linha["consultorio"]
            if status == AGUARDANDO:
                sistema.cadastrar(nome, horario, prioridade, id_paciente)
                continue

            paciente = Paciente(id_paciente, nome, prioridade, float(horario_em_minutos(horario)))
            ficha = Ficha(paciente, horario)
            ficha.status = status
            ficha.consultorio = consultorio
            sistema.fichas.inserir(id_paciente, ficha)
            if status == EM_ATENDIMENTO:
                sistema.consultorios[consultorio - 1] = ficha
            else:
                sistema.historico.append(id_paciente)
        sistema.validar()
        return sistema

    @staticmethod
    def _gravar(conexao, sistema, ficha):
        ordem = len(sistema.historico) if ficha.status in (CANCELADO, CONCLUIDO) else None
        conexao.execute("""
            INSERT INTO fichas (id, nome, horario, prioridade, status, consultorio, ordem_encerramento)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                prioridade = excluded.prioridade,
                status = excluded.status,
                consultorio = excluded.consultorio,
                ordem_encerramento = excluded.ordem_encerramento
        """, (ficha.id, ficha.nome, ficha.horario, ficha.prioridade, ficha.status,
              ficha.consultorio, ordem))

    def _alterar(self, operacao):
        with self._conectar(escrita=True) as conexao:
            sistema = self._restaurar(conexao)
            ficha = operacao(sistema)
            sistema.validar()
            self._gravar(conexao, sistema, ficha)
            return ficha

    def cadastrar(self, nome, horario, prioridade, id_paciente=None):
        if isinstance(id_paciente, int) and id_paciente > ID_MAXIMO:
            raise ErroSIGAE(f"O número de atendimento deve ser menor ou igual a {ID_MAXIMO}.")
        return self._alterar(
            lambda sistema: sistema.cadastrar(nome, horario, prioridade, id_paciente)
        )

    def reclassificar(self, id_paciente, prioridade):
        return self._alterar(lambda sistema: sistema.reclassificar(id_paciente, prioridade)[0])

    def cancelar(self, id_paciente):
        return self._alterar(lambda sistema: sistema.cancelar(id_paciente))

    def chamar(self, consultorio, id_esperado, prioridade_esperada=None):
        def chamar_proximo(sistema):
            proximo = sistema.proximo_da_fila()
            if proximo is None or proximo.id != id_esperado:
                raise ErroSIGAE("A fila mudou. Confira o próximo paciente e tente novamente.")
            if prioridade_esperada is not None and proximo.prioridade != prioridade_esperada:
                raise ErroSIGAE("A classificação mudou. Confira a próxima senha e tente novamente.")
            return sistema.chamar_proximo(consultorio)

        return self._alterar(chamar_proximo)

    def concluir(self, consultorio, id_esperado):
        if consultorio not in (1, 2):
            raise ErroSIGAE("Escolha o consultório 1 ou 2.")

        def concluir_atendimento(sistema):
            ficha = sistema.em_atendimento()[consultorio - 1]
            if ficha is None or ficha.id != id_esperado:
                raise ErroSIGAE("O consultório mudou. Confira o atendimento e tente novamente.")
            return sistema.concluir(consultorio)

        return self._alterar(concluir_atendimento)

    def carregar_exemplos(self, cenario):
        with self._conectar(escrita=True) as conexao:
            if conexao.execute("SELECT 1 FROM fichas LIMIT 1").fetchone():
                raise ErroSIGAE("Os cenários de exemplo só podem ser carregados em uma base vazia.")
            sistema = SIGAE()
            sistema.carregar(cenario)
            for ficha in sistema.lista_por_chegada():
                self._gravar(conexao, sistema, ficha)
