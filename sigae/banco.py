import os
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from sigae.modelos.paciente import Paciente
from sigae.sistema import (
    AGUARDANDO,
    CANCELADO,
    CONCLUIDO,
    ErroSIGAE,
    Ficha,
    SIGAE,
    horario_em_minutos,
)

BANCO_PADRAO = Path(__file__).resolve().parent.parent / "sigae.db"
ID_MAXIMO = 2**63 - 1
VERSAO_BANCO = 2


class BancoSIGAE:
    def __init__(self, caminho=None):
        self.caminho = caminho or os.environ.get("SIGAE_DB_PATH") or BANCO_PADRAO
        with self._conectar() as conexao:
            versao = conexao.execute("PRAGMA user_version").fetchone()[0]
        if versao != VERSAO_BANCO:
            with self._conectar(escrita=True) as conexao:
                versao = conexao.execute("PRAGMA user_version").fetchone()[0]
                if versao in (0, 1):
                    self._migrar(conexao, versao)
                elif versao != VERSAO_BANCO:
                    raise ErroSIGAE(f"Versão de banco incompatível: {versao}.")

    @staticmethod
    def _migrar(conexao, versao):
        legado = conexao.execute(
            "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'fichas'"
        ).fetchone()
        if legado:
            conexao.execute("ALTER TABLE fichas RENAME TO fichas_legado")

        conexao.execute("""
            CREATE TABLE medicos (
                id INTEGER PRIMARY KEY CHECK (id > 0),
                nome TEXT NOT NULL CHECK (length(nome) BETWEEN 1 AND 90),
                registro TEXT NOT NULL UNIQUE CHECK (length(registro) BETWEEN 1 AND 24)
            )
        """)
        conexao.execute("""
            CREATE TABLE fichas (
                id INTEGER PRIMARY KEY CHECK (id > 0),
                nome TEXT NOT NULL CHECK (length(nome) BETWEEN 2 AND 90),
                horario TEXT NOT NULL,
                prioridade INTEGER NOT NULL CHECK (prioridade BETWEEN 1 AND 5),
                status TEXT NOT NULL,
                medico_id INTEGER REFERENCES medicos(id),
                inicio TEXT,
                ordem_chamada INTEGER UNIQUE CHECK (ordem_chamada > 0),
                ordem_encerramento INTEGER UNIQUE CHECK (ordem_encerramento > 0),
                CHECK (
                    (medico_id IS NULL AND ordem_chamada IS NULL AND inicio IS NULL)
                    OR (medico_id IS NOT NULL AND ordem_chamada IS NOT NULL)
                ),
                CHECK (
                    (status = 'Aguardando' AND medico_id IS NULL AND ordem_encerramento IS NULL)
                    OR (status = 'Em atendimento' AND medico_id IS NOT NULL AND ordem_encerramento IS NULL)
                    OR (status = 'Concluído' AND medico_id IS NOT NULL AND ordem_encerramento IS NOT NULL)
                    OR (status = 'Cancelado' AND ordem_encerramento IS NOT NULL)
                )
            )
        """)

        if legado:
            conexao.execute("""
                INSERT INTO medicos (id, nome, registro)
                SELECT DISTINCT consultorio, 'Médico legado ' || consultorio, 'LEGADO-' || consultorio
                FROM fichas_legado WHERE consultorio IS NOT NULL
            """)
            conexao.execute("""
                INSERT INTO fichas
                    (id, nome, horario, prioridade, status, medico_id, ordem_chamada, ordem_encerramento)
                SELECT id, nome, horario,
                       CASE WHEN ? = 0 THEN prioridade WHEN prioridade = 1 THEN 3 ELSE 5 END,
                       status, consultorio,
                       CASE WHEN consultorio IS NOT NULL THEN ROW_NUMBER() OVER (ORDER BY id) END,
                       ordem_encerramento
                FROM fichas_legado
            """, (versao,))
            conexao.execute("DROP TABLE fichas_legado")

        conexao.execute("""
            CREATE UNIQUE INDEX medico_ocupado
            ON fichas(medico_id) WHERE status = 'Em atendimento'
        """)
        conexao.execute("PRAGMA user_version = 2")

    @contextmanager
    def _conectar(self, escrita=False):
        with closing(sqlite3.connect(self.caminho, timeout=10)) as conexao, conexao:
            conexao.row_factory = sqlite3.Row
            conexao.execute("PRAGMA foreign_keys = ON")
            conexao.execute("BEGIN IMMEDIATE" if escrita else "BEGIN")
            yield conexao

    def carregar(self):
        with self._conectar() as conexao:
            return self._restaurar(conexao)

    @staticmethod
    def _restaurar(conexao):
        sistema = SIGAE()
        for linha in conexao.execute("SELECT id, nome, registro FROM medicos ORDER BY id"):
            sistema.cadastrar_medico(linha["nome"], linha["registro"], linha["id"])

        linhas = conexao.execute("""
            SELECT id, nome, horario, prioridade, status, medico_id, inicio, ordem_chamada
            FROM fichas ORDER BY ordem_encerramento, id
        """)
        for linha in linhas:
            id_paciente = linha["id"]
            nome, horario, prioridade = linha["nome"], linha["horario"], linha["prioridade"]
            status = linha["status"]
            if status == AGUARDANDO:
                sistema.cadastrar(nome, horario, prioridade, id_paciente)
                continue

            paciente = Paciente(id_paciente, nome, prioridade, float(horario_em_minutos(horario)))
            ficha = Ficha(paciente, horario)
            ficha.status = status
            ficha.medico_id = linha["medico_id"]
            ficha.inicio = linha["inicio"]
            ficha.ordem_chamada = linha["ordem_chamada"]
            sistema.fichas.inserir(id_paciente, ficha)
            if status in (CANCELADO, CONCLUIDO):
                sistema.historico.append(id_paciente)
        sistema.restaurar_vinculos()
        sistema.validar()
        return sistema

    @staticmethod
    def _gravar(conexao, sistema, ficha):
        ordem = len(sistema.historico) if ficha.status in (CANCELADO, CONCLUIDO) else None
        conexao.execute("""
            INSERT INTO fichas
                (id, nome, horario, prioridade, status, medico_id, inicio, ordem_chamada, ordem_encerramento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                prioridade = excluded.prioridade,
                status = excluded.status,
                medico_id = excluded.medico_id,
                inicio = excluded.inicio,
                ordem_chamada = excluded.ordem_chamada,
                ordem_encerramento = excluded.ordem_encerramento
        """, (ficha.id, ficha.nome, ficha.horario, ficha.prioridade, ficha.status,
              ficha.medico_id, ficha.inicio, ficha.ordem_chamada, ordem))

    def _alterar(self, operacao):
        with self._conectar(escrita=True) as conexao:
            sistema = self._restaurar(conexao)
            ficha = operacao(sistema)
            sistema.validar()
            self._gravar(conexao, sistema, ficha)
            return ficha

    def cadastrar(self, nome, horario, prioridade):
        return self._alterar(lambda sistema: sistema.cadastrar(nome, horario, prioridade))

    def cadastrar_medico(self, nome, registro):
        with self._conectar(escrita=True) as conexao:
            sistema = self._restaurar(conexao)
            medico = sistema.cadastrar_medico(nome, registro)
            sistema.validar()
            conexao.execute(
                "INSERT INTO medicos (id, nome, registro) VALUES (?, ?, ?)",
                (medico.id, medico.nome, medico.registro),
            )
            return medico

    def reclassificar(self, id_paciente, prioridade):
        return self._alterar(lambda sistema: sistema.reclassificar(id_paciente, prioridade)[0])

    def cancelar(self, id_paciente, situacao_esperada):
        return self._alterar(lambda sistema: sistema.cancelar(id_paciente, situacao_esperada))

    def chamar(self, id_esperado, prioridade_esperada):
        def chamar_proximo(sistema):
            proximo = sistema.proximo_da_fila()
            if proximo is None or (proximo.id, proximo.prioridade) != (id_esperado, prioridade_esperada):
                raise ErroSIGAE("A fila mudou. Confira o próximo paciente e tente novamente.")
            return sistema.chamar_proximo()

        return self._alterar(chamar_proximo)

    def concluir(self, id_paciente):
        return self._alterar(lambda sistema: sistema.concluir(id_paciente))

    def carregar_exemplos(self, cenario):
        with self._conectar(escrita=True) as conexao:
            if conexao.execute("SELECT 1 FROM fichas LIMIT 1").fetchone():
                raise ErroSIGAE("Os cenários de exemplo só podem ser carregados em uma base sem fichas.")
            sistema = SIGAE()
            sistema.carregar(cenario)
            for ficha in sistema.lista_por_chegada():
                self._gravar(conexao, sistema, ficha)
