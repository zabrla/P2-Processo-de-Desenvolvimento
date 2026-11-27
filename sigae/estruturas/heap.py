from sigae.estruturas.tabela_hash import TabelaHash

class MinHeap:

    def __init__(self):
        self.v = []
        self.pos = TabelaHash()

    def __len__(self):
        return len(self.v)

    def __contains__(self, id_paciente):
        return self.pos.contem(id_paciente)

    @staticmethod
    def _validar_prioridade(prioridade):
        if not 1 <= prioridade <= 5:
            raise ValueError("a classificação deve estar entre 1 e 5")

    def _antes(self, i, j):
        return self.v[i].chave() < self.v[j].chave()

    def _trocar(self, i, j):
        self.v[i], self.v[j] = self.v[j], self.v[i]
        self.pos.atualizar(self.v[i].id, i)
        self.pos.atualizar(self.v[j].id, j)

    def _subir(self, i):
        while i > 0:
            pai = (i - 1) // 2
            if not self._antes(i, pai):
                break
            self._trocar(i, pai)
            i = pai

    def _descer(self, i):
        n = len(self.v)
        while True:
            esq = 2 * i + 1
            dir = 2 * i + 2
            menor = i
            if esq < n and self._antes(esq, menor):
                menor = esq
            if dir < n and self._antes(dir, menor):
                menor = dir
            if menor == i:
                break
            self._trocar(i, menor)
            i = menor

    def inserir(self, elemento):
        if self.pos.contem(elemento.id):
            raise KeyError(f"item {elemento.id} já está no heap")
        self.v.append(elemento)
        self.pos.inserir(elemento.id, len(self.v) - 1)
        self._subir(len(self.v) - 1)

    def posicao(self, id_item):
        i = self.pos.buscar(id_item)
        if i is None:
            raise KeyError(f"item {id_item} não está no heap")
        return i

    def buscar(self, id_item):
        i = self.pos.buscar(id_item)
        return None if i is None else self.v[i]

    def ids(self):
        return [elemento.id for elemento in self.v]

    def topo(self):
        return self.v[0] if self.v else None

    def extrair_min(self):
        if not self.v:
            return None
        raiz = self.v[0]
        ultimo = len(self.v) - 1
        self._trocar(0, ultimo)
        self.v.pop()
        self.pos.remover(raiz.id)
        if self.v:
            self._descer(0)
        return raiz

    def remover(self, id_item):
        i = self.posicao(id_item)
        removido = self.v[i]
        ultimo = len(self.v) - 1
        self._trocar(i, ultimo)
        self.v.pop()
        self.pos.remover(id_item)
        if i < len(self.v):
            movido = self.v[i].id
            self._subir(i)
            self._descer(self.pos.buscar(movido))
        return removido

    def alterar_prioridade(self, id_paciente, nova_prioridade):
        self._validar_prioridade(nova_prioridade)
        i = self.posicao(id_paciente)
        antiga = self.v[i].prioridade
        self.v[i].prioridade = nova_prioridade
        if nova_prioridade < antiga:
            self._subir(i)
        elif nova_prioridade > antiga:
            self._descer(i)
