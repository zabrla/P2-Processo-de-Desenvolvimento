from sigae.modelos.paciente import Paciente

class MinHeap:

    def __init__(self):
        self.v = []
        self.pos = {} 

    def __len__(self):
        return len(self.v)

    def __contains__(self, id_paciente):
        return id_paciente in self.pos

    @staticmethod
    def _validar_prioridade(prioridade):
        if prioridade not in (1, 2):
            raise ValueError("a classificação deve ser Prioridade (1) ou Normal (2)")

    def _antes(self, i, j):
        return self.v[i].chave() < self.v[j].chave()

    def _trocar(self, i, j):
        self.v[i], self.v[j] = self.v[j], self.v[i]
        self.pos[self.v[i].id] = i
        self.pos[self.v[j].id] = j

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

    def inserir(self, paciente: Paciente):
        self._validar_prioridade(paciente.prioridade)
        if paciente.id in self.pos:
            raise KeyError(f"paciente {paciente.id} já está no heap")
        self.v.append(paciente)
        self.pos[paciente.id] = len(self.v) - 1
        self._subir(len(self.v) - 1)

    def topo(self):
        return self.v[0] if self.v else None

    def extrair_min(self):
        if not self.v:
            return None
        raiz = self.v[0]
        ultimo = len(self.v) - 1
        self._trocar(0, ultimo)
        self.v.pop()
        del self.pos[raiz.id]
        if self.v:
            self._descer(0)
        return raiz

    def remover(self, id_paciente):
        if id_paciente not in self.pos:
            raise KeyError(f"paciente {id_paciente} não está no heap")
        i = self.pos[id_paciente]
        removido = self.v[i]
        ultimo = len(self.v) - 1
        self._trocar(i, ultimo)
        self.v.pop()
        del self.pos[id_paciente]
        if i < len(self.v):
            movido = self.v[i].id
            self._subir(i)
            self._descer(self.pos[movido])
        return removido

    def alterar_prioridade(self, id_paciente, nova_prioridade):
        self._validar_prioridade(nova_prioridade)
        if id_paciente not in self.pos:
            raise KeyError(f"paciente {id_paciente} não está no heap")
        i = self.pos[id_paciente]
        antiga = self.v[i].prioridade
        self.v[i].prioridade = nova_prioridade
        if nova_prioridade < antiga:
            self._subir(i)
        elif nova_prioridade > antiga:
            self._descer(i)