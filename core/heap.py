from core.paciente import Paciente

class MinHeap:

    def __init__(self):
        self.v = []

    def __len__(self):
        return len(self.v)

    def _antes(self, i, j):
        return self.v[i].chave() < self.v[j].chave()

    def _trocar(self, i, j):
        self.v[i], self.v[j] = self.v[j], self.v[i]

    def _subir(self, i):
        while i > 0:
            pai = (i - 1) // 2
            if not self._antes(i, pai):
                break
            self._trocar(i, pai)
            i = pai

    def inserir(self, paciente: Paciente):      
        if not 1 <= paciente.prioridade <= 5:
            raise ValueError("prioridade deve estar entre 1 e 5")
        self.v.append(paciente)
        self._subir(len(self.v) - 1)

    def topo(self):                             
        return self.v[0] if self.v else None
