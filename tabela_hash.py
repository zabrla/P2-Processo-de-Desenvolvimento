class NoHash:
    __slots__ = ("chave", "valor", "proximo")

    def __init__(self, chave, valor, proximo=None):
        self.chave = chave
        self.valor = valor
        self.proximo = proximo


def _eh_primo(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True


def _proximo_primo(n):
    while not _eh_primo(n):
        n += 1
    return n


class TabelaHash:

    CARGA_MAXIMA = 0.75

    def __init__(self, capacidade=11):
        self._capacidade = _proximo_primo(max(capacidade, 2))
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

        if self.fator_carga() > self.CARGA_MAXIMA:
            self._redimensionar(self._capacidade * 2)

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

    def _redimensionar(self, nova_capacidade):
        antigos = self._buckets
        self._capacidade = _proximo_primo(nova_capacidade)
        self._buckets = [None] * self._capacidade

        for cabeca in antigos:
            atual = cabeca
            while atual is not None:
                proximo = atual.proximo
                indice = self._hash(atual.chave)
                atual.proximo = self._buckets[indice]
                self._buckets[indice] = atual
                atual = proximo

    def fator_carga(self):
        return self._tamanho / self._capacidade

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

    def colisoes(self):
        total = 0
        for cabeca in self._buckets:
            if cabeca is not None:
                atual = cabeca.proximo
                while atual is not None:
                    total += 1
                    atual = atual.proximo
        return total

    def validar(self):
        contados = 0
        vistos = TabelaHash.__new__(TabelaHash)
        vistos._capacidade = _proximo_primo(max(self._tamanho * 2, 11))
        vistos._buckets = [None] * vistos._capacidade
        vistos._tamanho = 0

        for indice, cabeca in enumerate(self._buckets):
            atual = cabeca
            while atual is not None:
                esperado = self._hash(atual.chave)
                if esperado != indice:
                    raise AssertionError(
                        f"ID {atual.chave} está no bucket {indice}, deveria estar no {esperado}"
                    )
                if vistos.contem(atual.chave):
                    raise AssertionError(f"ID {atual.chave} duplicado")
                vistos._buckets[vistos._hash(atual.chave)] = NoHash(
                    atual.chave, None, vistos._buckets[vistos._hash(atual.chave)]
                )
                contados += 1
                atual = atual.proximo

        if contados != self._tamanho:
            raise AssertionError(f"Tamanho registrado {self._tamanho}, mas há {contados} nós")
        return True

    def exibir(self):
        linhas = []
        for indice, cabeca in enumerate(self._buckets):
            ids = []
            atual = cabeca
            while atual is not None:
                ids.append(str(atual.chave))
                atual = atual.proximo
            linhas.append(f"[{indice:>2}] " + (" -> ".join(ids) if ids else "—"))
        linhas.append(
            f"Capacidade {self._capacidade} · Registros {self._tamanho} · "
            f"Colisões {self.colisoes()} · Carga {self.fator_carga():.0%}"
        )
        return "\n".join(linhas)
