RED = 0
BLACK = 1


class No:
    def __init__(self, chave, dado=None):
        self.chave = chave
        self.dado = dado
        self.cor = RED
        self.esq = None
        self.dir = None
        self.pai = None


class ArvoreRubroNegra:
    def __init__(self):
        self.NIL = No(chave=None)
        self.NIL.cor = BLACK
        self.raiz = self.NIL

    def inserir(self, horario, id_paciente, dado=None):
        chave_composta = (horario, id_paciente)
        novo_no = No(chave_composta, dado)
        novo_no.esq = self.NIL
        novo_no.dir = self.NIL

        pai_atual = None
        atual = self.raiz

        while atual != self.NIL:
            pai_atual = atual
            if novo_no.chave < atual.chave:
                atual = atual.esq
            elif novo_no.chave > atual.chave:
                atual = atual.dir
            else:
                raise ValueError(f"chave duplicada na arvore rubro negra: {chave_composta}")

        novo_no.pai = pai_atual

        if pai_atual is None:
            self.raiz = novo_no
        elif novo_no.chave < pai_atual.chave:
            pai_atual.esq = novo_no
        else:
            pai_atual.dir = novo_no

        if novo_no.pai is None:
            novo_no.cor = BLACK
            return

        if novo_no.pai.pai is None:
            return

        self._corrigir_insercao(novo_no)

    def _corrigir_insercao(self, z):
        while z.pai is not None and z.pai.cor == RED:
            avo = z.pai.pai

            if z.pai == avo.esq:
                tio = avo.dir

                if tio.cor == RED:
                    z.pai.cor = BLACK
                    tio.cor = BLACK
                    avo.cor = RED
                    z = avo
                else:
                    if z == z.pai.dir:
                        z = z.pai
                        self._rotacao_esquerda(z)

                    z.pai.cor = BLACK
                    avo.cor = RED
                    self._rotacao_direita(avo)

            else:
                tio = avo.esq

                if tio.cor == RED:
                    z.pai.cor = BLACK
                    tio.cor = BLACK
                    avo.cor = RED
                    z = avo
                else:
                    if z == z.pai.esq:
                        z = z.pai
                        self._rotacao_direita(z)

                    z.pai.cor = BLACK
                    avo.cor = RED
                    self._rotacao_esquerda(avo)

        self.raiz.cor = BLACK

    def _rotacao_esquerda(self, x):
        y = x.dir
        x.dir = y.esq

        if y.esq != self.NIL:
            y.esq.pai = x

        y.pai = x.pai

        if x.pai is None:
            self.raiz = y
        elif x == x.pai.esq:
            x.pai.esq = y
        else:
            x.pai.dir = y

        y.esq = x
        x.pai = y

    def _rotacao_direita(self, x):
        y = x.esq
        x.esq = y.dir

        if y.dir != self.NIL:
            y.dir.pai = x

        y.pai = x.pai

        if x.pai is None:
            self.raiz = y
        elif x == x.pai.dir:
            x.pai.dir = y
        else:
            x.pai.esq = y

        y.dir = x
        x.pai = y


""" 
TESTE

if __name__ == "__main__":
    arn = ArvoreRubroNegra()

    arn.inserir("08:30", 102, {"nome": "ana"})
    arn.inserir("08:15", 101, {"nome": "carlos"})
    arn.inserir("08:30", 100, {"nome": "beatriz"})
    arn.inserir("09:00", 103, {"nome": "daniel"})

    print("raiz da árvore:", arn.raiz.chave, "| Cor (1=BLACK):", arn.raiz.cor)
    print("filho esquerdo da raiz:", arn.raiz.esq.chave)
    print("filho direito da raiz:", arn.raiz.dir.chave)
"""