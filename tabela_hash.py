class NoHash:
    __slots__ = ("chave", "valor", "proximo")

    def __init__(self, chave, valor, proximo=None):
        self.chave = chave
        self.valor = valor
        self.proximo = proximo


class TabelaHash:
    """Tabela hash com encadeamento separado."""

    def __init__(self, capacidade=11):
        self._capacidade = capacidade
        self._buckets = [None] * self._capacidade
        self._tamanho = 0

    def _hash(self, chave):
        return chave % self._capacidade

    def inserir(self, chave, valor):
        if not isinstance(chave, int) or isinstance(chave, bool):
            raise TypeError("A chave (ID) deve ser um inteiro")

        indice = self._hash(chave)
        atual = self._buckets[indice]
        while atual is not None:
            if atual.chave == chave:
                raise KeyError(f"ID {chave} já cadastrado")
            atual = atual.proximo

        self._buckets[indice] = NoHash(chave, valor, self._buckets[indice])
        self._tamanho += 1

    def buscar(self, chave):
        atual = self._buckets[self._hash(chave)]
        while atual is not None:
            if atual.chave == chave:
                return atual.valor
            atual = atual.proximo
        return None

    def contem(self, chave):
        atual = self._buckets[self._hash(chave)]
        while atual is not None:
            if atual.chave == chave:
                return True
            atual = atual.proximo
        return False

    def atualizar(self, chave, valor):
        atual = self._buckets[self._hash(chave)]
        while atual is not None:
            if atual.chave == chave:
                atual.valor = valor
                return
            atual = atual.proximo
        raise KeyError(f"ID {chave} não encontrado")

    def remover(self, chave):
        indice = self._hash(chave)
        anterior = None
        atual = self._buckets[indice]
        while atual is not None:
            if atual.chave == chave:
                if anterior is None:
                    self._buckets[indice] = atual.proximo
                else:
                    anterior.proximo = atual.proximo
                self._tamanho -= 1
                return atual.valor
            anterior = atual
            atual = atual.proximo
        raise KeyError(f"ID {chave} não encontrado")

    def capacidade(self):
        return self._capacidade

    def __len__(self):
        return self._tamanho

    def chaves(self):
        resultado = []
        for cabeca in self._buckets:
            atual = cabeca
            while atual is not None:
                resultado.append(atual.chave)
                atual = atual.proximo
        return resultado
