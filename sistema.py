from core.paciente import Paciente
from core.heap import MinHeap
from arvore_rubro_negra import ArvoreRubroNegra
from tabela_hash import TabelaHash

AGUARDANDO = "Aguardando"
EM_ATENDIMENTO = "Em atendimento"
CONCLUIDO = "Concluído"
CANCELADO = "Cancelado"

# Índice = prioridade (a posição 0 não é usada).
CLASSIFICACOES = ("", "Emergência", "Muito urgente", "Urgente", "Pouco urgente", "Não urgente")


class ErroSIGAE(Exception):
    """Erro de regra de negócio, mostrado para o operador."""


class Ficha:
    """Tudo o que o sistema sabe sobre um paciente, inclusive depois que ele sai da fila."""

    __slots__ = ("paciente", "horario", "status", "consultorio")

    def __init__(self, paciente, horario):
        self.paciente = paciente
        self.horario = horario
        self.status = AGUARDANDO
        self.consultorio = None

    @property
    def id(self):
        return self.paciente.id

    @property
    def nome(self):
        return self.paciente.nome

    @property
    def prioridade(self):
        return self.paciente.prioridade

    def resumo(self):
        texto = (f"#{self.id} {self.nome} · chegou {self.horario} · "
                 f"P{self.prioridade} {CLASSIFICACOES[self.prioridade]} · {self.status}")
        if self.consultorio is not None:
            texto += f" (médico {self.consultorio})"
        return texto


def horario_em_minutos(horario):
    if not isinstance(horario, str) or len(horario) != 5 or horario[2] != ":":
        raise ErroSIGAE("Horário deve estar no formato HH:MM, por exemplo 08:05.")
    horas, minutos = horario[:2], horario[3:]
    if not (horas.isdigit() and minutos.isdigit()):
        raise ErroSIGAE("Horário deve conter só números, no formato HH:MM.")
    horas, minutos = int(horas), int(minutos)
    if not (0 <= horas <= 23 and 0 <= minutos <= 59):
        raise ErroSIGAE("Horário fora do intervalo 00:00 a 23:59.")
    return horas * 60 + minutos


def remover_do_heap(heap, id_paciente):
    """Remove um paciente qualquer do heap em O(log n).

    O MinHeap do grupo ainda não tem remover(id). Enquanto não tiver, a remoção é
    feita aqui usando as operações internas dele: troca com o último, tira o último
    e reposiciona quem foi para o lugar do removido.
    """
    if hasattr(heap, "remover"):
        return heap.remover(id_paciente)

    if id_paciente not in heap:
        raise KeyError(f"paciente {id_paciente} não está no heap")

    i = heap.pos[id_paciente]
    removido = heap.v[i]
    ultimo = len(heap.v) - 1
    heap._trocar(i, ultimo)
    heap.v.pop()
    del heap.pos[id_paciente]

    if i < len(heap.v):
        # O elemento que veio do fim pode precisar subir ou descer.
        movido = heap.v[i].id
        heap._subir(i)
        heap._descer(heap.pos[movido])
    return removido


class SIGAE:
    """Integra Tabela Hash, Árvore Rubro-Negra e Min-Heap.

    Os três índices guardam exatamente os pacientes que estão AGUARDANDO.
    Quem é chamado, concluído ou cancelado sai dos três e fica só nas fichas.
    """

    def __init__(self, consultorios=2):
        self.num_consultorios = consultorios
        self.limpar()

    def limpar(self):
        self.espera = TabelaHash()      # ID -> Paciente (só quem aguarda)
        self.arvore = ArvoreRubroNegra()  # (horário, ID) -> Paciente
        self.heap = MinHeap()           # prioridade, chegada, ID
        self.fichas = TabelaHash()      # ID -> Ficha (todos que já passaram pelo sistema)
        self.consultorios = [None] * self.num_consultorios
        self.historico = []             # IDs na ordem em que saíram (concluídos e cancelados)
        self.proximo_id = 1000

    # ---------- cadastro ----------

    def cadastrar(self, nome, horario, prioridade, id_paciente=None):
        nome = (nome or "").strip()
        if not 2 <= len(nome) <= 90:
            raise ErroSIGAE("Informe um nome entre 2 e 90 caracteres.")
        self._checar_prioridade(prioridade)
        chegada = horario_em_minutos(horario)

        if id_paciente is None:
            id_paciente = self._gerar_id()
        elif not isinstance(id_paciente, int) or isinstance(id_paciente, bool) or id_paciente <= 0:
            raise ErroSIGAE("O número de atendimento deve ser um inteiro positivo.")
        elif self.fichas.contem(id_paciente):
            raise ErroSIGAE(f"O número {id_paciente} já foi usado.")

        paciente = Paciente(id_paciente, nome, prioridade, float(chegada))
        ficha = Ficha(paciente, horario)

        # Ou entra nas três estruturas, ou não entra em nenhuma.
        feitos = []
        try:
            self.espera.inserir(id_paciente, paciente)
            feitos.append("hash")
            self.arvore.inserir(horario, id_paciente, paciente)
            feitos.append("arvore")
            self.heap.inserir(paciente)
            feitos.append("heap")
            self.fichas.inserir(id_paciente, ficha)
        except Exception as erro:
            self._desfazer_cadastro(feitos, paciente, horario)
            raise ErroSIGAE(f"Cadastro desfeito, nenhuma estrutura foi alterada ({erro}).") from erro

        return ficha

    def _gerar_id(self):
        # Pula números que já foram usados num cadastro com ID manual.
        while self.fichas.contem(self.proximo_id):
            self.proximo_id += 1
        id_paciente = self.proximo_id
        self.proximo_id += 1
        return id_paciente

    def _desfazer_cadastro(self, feitos, paciente, horario):
        if "heap" in feitos:
            remover_do_heap(self.heap, paciente.id)
        if "arvore" in feitos:
            self.arvore.remover(horario, paciente.id)
        if "hash" in feitos:
            self.espera.remover(paciente.id)

    # ---------- consultas ----------

    def localizar(self, id_paciente):
        """Busca só pela Tabela Hash."""
        ficha = self.fichas.buscar(id_paciente)
        if ficha is None:
            raise ErroSIGAE(f"Atendimento #{id_paciente} não localizado.")
        return ficha

    def lista_por_chegada(self):
        """Percurso em ordem da Rubro-Negra = ordem de chegada."""
        return [self.fichas.buscar(paciente.id) for _, paciente in self.arvore.percurso_em_ordem()]

    def proximo_da_fila(self):
        paciente = self.heap.topo()
        return None if paciente is None else self.fichas.buscar(paciente.id)

    def em_atendimento(self):
        return list(self.consultorios)

    def fichas_do_historico(self):
        return [self.fichas.buscar(i) for i in reversed(self.historico)]

    def aguardando(self):
        return len(self.espera)

    def concluidos(self):
        return sum(1 for i in self.historico if self.fichas.buscar(i).status == CONCLUIDO)

    # ---------- alterações ----------

    def reclassificar(self, id_paciente, nova_prioridade):
        self._checar_prioridade(nova_prioridade)
        ficha = self._ficha_em_espera(id_paciente)
        antiga = ficha.prioridade
        if nova_prioridade != antiga:
            self.heap.alterar_prioridade(id_paciente, nova_prioridade)
        return ficha, antiga

    def cancelar(self, id_paciente):
        ficha = self._retirar_da_espera(id_paciente)
        ficha.status = CANCELADO
        self.historico.append(ficha.id)
        return ficha

    def chamar_proximo(self, consultorio=None):
        if consultorio is None:
            consultorio = self._primeiro_consultorio_livre()
            if consultorio is None:
                raise ErroSIGAE("Os dois médicos estão em atendimento. Conclua um atendimento antes de chamar.")
        else:
            self._checar_consultorio(consultorio)
            if self.consultorios[consultorio - 1] is not None:
                raise ErroSIGAE(f"O médico {consultorio} já está em atendimento.")

        proximo = self.heap.topo()
        if proximo is None:
            raise ErroSIGAE("Não há pacientes aguardando.")

        ficha = self._retirar_da_espera(proximo.id)
        ficha.status = EM_ATENDIMENTO
        ficha.consultorio = consultorio
        self.consultorios[consultorio - 1] = ficha
        return ficha

    def concluir(self, consultorio=None):
        ocupados = [i + 1 for i, f in enumerate(self.consultorios) if f is not None]
        if not ocupados:
            raise ErroSIGAE("Nenhum paciente está em atendimento.")
        if consultorio is None:
            if len(ocupados) > 1:
                raise ErroSIGAE("Os dois médicos estão em atendimento; informe qual deve concluir.")
            consultorio = ocupados[0]
        self._checar_consultorio(consultorio)

        ficha = self.consultorios[consultorio - 1]
        if ficha is None:
            raise ErroSIGAE(f"O médico {consultorio} está livre.")
        ficha.status = CONCLUIDO
        self.consultorios[consultorio - 1] = None
        self.historico.append(ficha.id)
        return ficha

    # ---------- apoio ----------

    def _checar_prioridade(self, prioridade):
        if not isinstance(prioridade, int) or isinstance(prioridade, bool) or not 1 <= prioridade <= 5:
            raise ErroSIGAE("A classificação de risco deve ser de 1 a 5.")

    def _checar_consultorio(self, consultorio):
        if not isinstance(consultorio, int) or not 1 <= consultorio <= self.num_consultorios:
            raise ErroSIGAE(f"Médico deve ser de 1 a {self.num_consultorios}.")

    def _primeiro_consultorio_livre(self):
        for i, ficha in enumerate(self.consultorios):
            if ficha is None:
                return i + 1
        return None

    def _ficha_em_espera(self, id_paciente):
        if not self.espera.contem(id_paciente):
            ficha = self.fichas.buscar(id_paciente)
            if ficha is None:
                raise ErroSIGAE(f"Atendimento #{id_paciente} não localizado.")
            raise ErroSIGAE(f"#{id_paciente} não está aguardando ({ficha.status}).")
        return self.fichas.buscar(id_paciente)

    def _retirar_da_espera(self, id_paciente):
        ficha = self._ficha_em_espera(id_paciente)
        paciente, horario = ficha.paciente, ficha.horario

        # Se algo falhar no meio, devolve o paciente às estruturas de onde já saiu.
        removidos = []
        try:
            remover_do_heap(self.heap, id_paciente)
            removidos.append("heap")
            if not self.arvore.remover(horario, id_paciente):
                raise KeyError(f"({horario}, {id_paciente}) não encontrado na árvore")
            removidos.append("arvore")
            self.espera.remover(id_paciente)
        except Exception as erro:
            if "arvore" in removidos:
                self.arvore.inserir(horario, id_paciente, paciente)
            if "heap" in removidos:
                self.heap.inserir(paciente)
            raise ErroSIGAE(f"Operação desfeita, as estruturas não foram alteradas ({erro}).") from erro
        return ficha

    # ---------- validação ----------

    def validar(self):
        self.arvore.validar_propriedades()
        self.espera.validar()
        self.fichas.validar()
        self._validar_heap()

        ids_arvore = []
        for (horario, id_chave), paciente in self.arvore.percurso_em_ordem():
            if id_chave != paciente.id:
                raise AssertionError(f"Árvore: chave ({horario}, {id_chave}) aponta para o paciente #{paciente.id}.")
            ids_arvore.append(paciente.id)
        ids_heap = [paciente.id for paciente in self.heap.v]
        ids_hash = self.espera.chaves()

        referencia = sorted(ids_hash)
        for nome, ids in (("Árvore", ids_arvore), ("Heap", ids_heap)):
            if sorted(ids) != referencia:
                raise AssertionError(f"{nome} e Hash não têm os mesmos pacientes: {sorted(ids)} x {referencia}")

        for id_paciente in referencia:
            ficha = self.fichas.buscar(id_paciente)
            if ficha is None or ficha.status != AGUARDANDO:
                raise AssertionError(f"#{id_paciente} está nos índices mas não consta como aguardando.")
            if self.espera.buscar(id_paciente) is not ficha.paciente:
                raise AssertionError(f"#{id_paciente}: Hash e ficha apontam para registros diferentes.")

        em_atendimento = 0
        for numero, ficha in enumerate(self.consultorios, start=1):
            if ficha is None:
                continue
            em_atendimento += 1
            if ficha.status != EM_ATENDIMENTO or ficha.consultorio != numero:
                raise AssertionError(f"Médico {numero} com ficha em estado inválido.")
            if self.espera.contem(ficha.id):
                raise AssertionError(f"#{ficha.id} está em atendimento e continua na fila.")

        for id_paciente in self.historico:
            ficha = self.fichas.buscar(id_paciente)
            if ficha.status not in (CONCLUIDO, CANCELADO) or self.espera.contem(id_paciente):
                raise AssertionError(f"#{id_paciente} está no histórico com estado inválido.")

        total = len(referencia) + em_atendimento + len(self.historico)
        if total != len(self.fichas):
            raise AssertionError(f"{len(self.fichas)} fichas, mas {total} pacientes localizados nos estados.")
        return True

    def _validar_heap(self):
        if len(self.heap.pos) != len(self.heap.v):
            raise AssertionError("Heap: mapa de posições com tamanho diferente do vetor.")
        for i, paciente in enumerate(self.heap.v):
            if self.heap.pos.get(paciente.id) != i:
                raise AssertionError(f"Heap: posição do paciente #{paciente.id} registrada errada.")
            if i > 0 and self.heap.v[(i - 1) // 2].chave() > paciente.chave():
                raise AssertionError(f"Heap: #{paciente.id} tem prioridade menor que o pai.")

    # ---------- cenários ----------

    CENARIO_PADRAO = (
        (1000, "Ana Ribeiro", "08:00", 4),
        (1001, "Bruno Souza", "08:05", 2),
        (1002, "Carlos Mendes", "08:10", 5),
        (1003, "Daniela Costa", "08:15", 1),
        (1004, "Eduardo Silva", "08:20", 3),
    )

    # Com capacidade 11, todos esses IDs caem no bucket 10.
    CENARIO_COLISAO = (
        (1000, "Ana Ribeiro", "08:00", 4),
        (1011, "Bruno Souza", "08:05", 2),
        (1022, "Carlos Mendes", "08:10", 5),
        (1033, "Daniela Costa", "08:15", 1),
        (1044, "Eduardo Silva", "08:20", 3),
    )

    def carregar(self, cenario):
        self.limpar()
        for id_paciente, nome, horario, prioridade in cenario:
            self.cadastrar(nome, horario, prioridade, id_paciente)
        if cenario:
            self.proximo_id = max(c[0] for c in cenario) + 1
