from core.heap import MinHeap
from core.paciente import Paciente

h = MinHeap()
h.inserir(Paciente(1, "Ana", 3, 10.0))
h.inserir(Paciente(2, "Bruno", 1, 12.0))
h.inserir(Paciente(3, "Carla", 1, 11.0))

print("Proximo:", h.topo().nome)

h.alterar_prioridade(1, 1)
print("Apos alterar prioridade da Ana:", h.topo().nome)

while len(h):
    p = h.extrair_min()
    print("Atendido:", p.nome, "(prioridade", str(p.prioridade) + ")")