from sigae.modelos.paciente import Paciente
from sigae.estruturas.heap import MinHeap
from sigae.estruturas.arvore_rubro_negra import ArvoreRubroNegra
from sigae.estruturas.tabela_hash import TabelaHash

AGUARDANDO = "Aguardando"
EM_ATENDIMENTO = "Em atendimento"
CONCLUIDO = "Concluído"
CANCELADO = "Cancelado"

CLASSIFICACOES = ("", "Emergência", "Muito urgente", "Urgente", "Pouco urgente", "Não urgente")


class ErroSIGAE(Exception):
    """Erro de regra de negócio, mostrado para o operador."""


class ErroIntegridade(ErroSIGAE):
    """Uma operação falhou E o desfazer também falhou: as estruturas podem estar divergentes."""


class Transacao:

    def __init__(self):
        self._desfazer = []

    def passo(self, fazer, desfazer):
        resultado = fazer()
        self._desfazer.append(desfazer)
        return resultado

    def __enter__(self):
        return self

    def __exit__(self, tipo, erro, _tb):
        if erro is None:
            return False
        falhas = []
        for desfazer in reversed(self._desfazer):
            try:
                desfazer()
            except Exception as falha:
                falhas.append(falha)
        if falhas:
            raise ErroIntegridade(
                f"Falha ao desfazer a operação ({erro}); desfazer falhou em {len(falhas)} passo(s): "
                f"{'; '.join(map(str, falhas))}. Recarregue o cenário."
            ) from erro
        if isinstance(erro, ErroSIGAE):
            return False  
        raise ErroSIGAE(f"Operação desfeita, nenhuma estrutura foi alterada ({erro}).") from erro


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


class SIGAE:
    """Integra Tabela Hash, Árvore Rubro-Negra e Min-Heap.

    Os três índices guardam exatamente os pacientes que estão AGUARDANDO.
    Quem é chamado, concluído ou cancelado sai dos três e fica só nas fichas.
    """

    def __init__(self, consultorios=2):
        self.num_consultorios = consultorios
        self.limpar()

    def limpar(self):
        self.espera = TabelaHash()
        self.arvore = ArvoreRubroNegra()
        self.heap = MinHeap()
        self.fichas = TabelaHash()
        self.consultorios = [None] * self.num_consultorios
        self.historico = []
        self.proximo_id = 1000


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

        with Transacao() as t:
            t.passo(lambda: self.espera.inserir(id_paciente, paciente),
                    lambda: self.espera.remover(id_paciente))
            t.passo(lambda: self.arvore.inserir(horario, id_paciente, paciente),
                    lambda: self._exigir(self.arvore.remover(horario, id_paciente), "árvore"))
            t.passo(lambda: self.heap.inserir(paciente),
                    lambda: self.heap.remover(id_paciente))
            t.passo(lambda: self.fichas.inserir(id_paciente, ficha),
                    lambda: self.fichas.remover(id_paciente))
            self._conferir_paciente(id_paciente, na_fila=True)

        return ficha

    def _gerar_id(self):
        while self.fichas.contem(self.proximo_id):
            self.proximo_id += 1
        id_paciente = self.proximo_id
        self.proximo_id += 1
        return id_paciente

    @staticmethod
    def _exigir(ok, estrutura):
        if not ok:
            raise KeyError(f"registro não encontrado na {estrutura}")


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


    def reclassificar(self, id_paciente, nova_prioridade):
        self._checar_prioridade(nova_prioridade)
        ficha = self._ficha_em_espera(id_paciente)
        antiga = ficha.prioridade
        if nova_prioridade != antiga:
            with Transacao() as t:
                t.passo(lambda: self.heap.alterar_prioridade(id_paciente, nova_prioridade),
                        lambda: self.heap.alterar_prioridade(id_paciente, antiga))
                self._conferir_paciente(id_paciente, na_fila=True)
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

        with Transacao() as t:
            self._conferir_paciente(id_paciente, na_fila=True)
            t.passo(lambda: self.heap.remover(id_paciente),
                    lambda: self.heap.inserir(paciente))
            t.passo(lambda: self._exigir(self.arvore.remover(horario, id_paciente), "árvore"),
                    lambda: self.arvore.inserir(horario, id_paciente, paciente))
            t.passo(lambda: self.espera.remover(id_paciente),
                    lambda: self.espera.inserir(id_paciente, paciente))
            self._conferir_paciente(id_paciente, na_fila=False)
        return ficha

    def _conferir_paciente(self, id_paciente, na_fila):
        ficha = self.fichas.buscar(id_paciente)
        if ficha is None:
            raise AssertionError(f"#{id_paciente} sem ficha.")
        no = self.arvore.buscar(ficha.horario, id_paciente)
        presente = {
            "Hash": self.espera.contem(id_paciente),
            "Árvore": no is not None,
            "Heap": id_paciente in self.heap,
        }
        divergentes = [nome for nome, esta in presente.items() if esta != na_fila]
        if divergentes:
            estado = "deveria estar" if na_fila else "não deveria estar"
            raise AssertionError(f"#{id_paciente} {estado} em: {', '.join(divergentes)}.")
        if na_fila:
            objetos = {
                "Hash": self.espera.buscar(id_paciente),
                "Árvore": no.dado,
                "Heap": self.heap.v[self.heap.pos[id_paciente]],
            }
            for nome, objeto in objetos.items():
                if objeto is not ficha.paciente:
                    raise AssertionError(f"#{id_paciente}: {nome} aponta para um registro diferente da ficha.")


    def validar(self):
        self.arvore.validar_propriedades()
        self.espera.validar()
        self.fichas.validar()
        self._validar_heap()

        fichas = {}
        for chave in self.fichas.chaves():
            ficha = self.fichas.buscar(chave)
            if ficha.id != chave:
                raise AssertionError(f"Fichas: chave {chave} guarda a ficha do paciente #{ficha.id}.")
            if ficha.paciente.chegada != horario_em_minutos(ficha.horario):
                raise AssertionError(f"#{chave}: horário {ficha.horario} não confere com a chegada do paciente.")
            fichas[chave] = ficha

        def coletar(nome, pares):
            ids = set()
            for id_paciente, paciente, horario in pares:
                if id_paciente in ids:
                    raise AssertionError(f"{nome}: #{id_paciente} duplicado.")
                ids.add(id_paciente)
                ficha = fichas.get(id_paciente)
                if ficha is None:
                    raise AssertionError(f"{nome}: #{id_paciente} é um registro órfão (sem ficha).")
                if paciente is not ficha.paciente:
                    raise AssertionError(f"{nome}: #{id_paciente} aponta para um registro diferente da ficha.")
                if horario is not None and horario != ficha.horario:
                    raise AssertionError(f"{nome}: #{id_paciente} indexado em {horario}, mas chegou {ficha.horario}.")
            return ids

        ids_hash = coletar("Hash", ((i, self.espera.buscar(i), None) for i in self.espera.chaves()))
        ids_arvore = coletar("Árvore", ((i, p, h) for (h, i), p in self.arvore.percurso_em_ordem()))
        ids_heap = coletar("Heap", ((p.id, p, None) for p in self.heap.v))

        for nome, ids in (("Árvore", ids_arvore), ("Heap", ids_heap)):
            if ids != ids_hash:
                faltando, sobrando = sorted(ids_hash - ids), sorted(ids - ids_hash)
                raise AssertionError(f"{nome} diverge da Hash — faltando: {faltando}, sobrando: {sobrando}.")

        atendidos = set()
        for numero, ficha in enumerate(self.consultorios, start=1):
            if ficha is None:
                continue
            if ficha.id in atendidos:
                raise AssertionError(f"#{ficha.id} está em dois médicos ao mesmo tempo.")
            atendidos.add(ficha.id)
            if fichas.get(ficha.id) is not ficha:
                raise AssertionError(f"Médico {numero}: ficha #{ficha.id} não é a registrada no sistema.")
            if ficha.status != EM_ATENDIMENTO or ficha.consultorio != numero:
                raise AssertionError(f"Médico {numero} com ficha em estado inválido.")

        if len(set(self.historico)) != len(self.historico):
            raise AssertionError("Histórico com ID duplicado.")
        encerrados = set(self.historico)

        for id_paciente, ficha in fichas.items():
            lugares = [nome for nome, ids in (("fila", ids_hash), ("atendimento", atendidos), ("histórico", encerrados)) if id_paciente in ids]
            if len(lugares) != 1:
                raise AssertionError(f"#{id_paciente} encontrado em {lugares or 'nenhum lugar'} (deve ser 1).")
            esperado = {"fila": (AGUARDANDO,), "atendimento": (EM_ATENDIMENTO,),
                        "histórico": (CONCLUIDO, CANCELADO)}[lugares[0]]
            if ficha.status not in esperado:
                raise AssertionError(f"#{id_paciente} está em {lugares[0]} com status {ficha.status}.")

        if not (ids_hash | atendidos | encerrados) <= fichas.keys():
            raise AssertionError("Há IDs em uso sem ficha correspondente.")
        return True

    def _validar_heap(self):
        if len(self.heap.pos) != len(self.heap.v):
            raise AssertionError("Heap: mapa de posições com tamanho diferente do vetor.")
        for i, paciente in enumerate(self.heap.v):
            if self.heap.pos.get(paciente.id) != i:
                raise AssertionError(f"Heap: posição do paciente #{paciente.id} registrada errada.")
            if i > 0 and self.heap.v[(i - 1) // 2].chave() > paciente.chave():
                raise AssertionError(f"Heap: #{paciente.id} tem prioridade menor que o pai.")


    CENARIO_PADRAO = (
        (1000, "Ana Ribeiro", "08:00", 4),
        (1001, "Bruno Souza", "08:05", 2),
        (1002, "Carlos Mendes", "08:10", 5),
        (1003, "Daniela Costa", "08:15", 1),
        (1004, "Eduardo Silva", "08:20", 3),
    )

    CENARIO_COLISAO = (
        (1000, "Ana Ribeiro", "08:00", 4),
        (1011, "Bruno Souza", "08:05", 2),
        (1022, "Carlos Mendes", "08:10", 5),
        (1033, "Daniela Costa", "08:15", 1),
        (1044, "Eduardo Silva", "08:20", 3),
    )

    def carregar(self, cenario):
        novo = SIGAE(self.num_consultorios)
        for id_paciente, nome, horario, prioridade in cenario:
            novo.cadastrar(nome, horario, prioridade, id_paciente)
        if cenario:
            novo.proximo_id = max(c[0] for c in cenario) + 1
        novo.validar()
        self.__dict__.update(novo.__dict__)
