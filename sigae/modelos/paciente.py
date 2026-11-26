from dataclasses import dataclass

@dataclass
class Paciente:
    id: int
    nome: str
    prioridade: int     
    chegada: float

    def chave(self):
        return (self.prioridade, self.chegada, self.id)
