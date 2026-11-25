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
        self.NIL.esq = self.NIL
        self.NIL.dir = self.NIL
        self.raiz = self.NIL

    def _validar_horario(self, horario):
        if not isinstance(horario, str) or len(horario) != 5 or horario[2] != ":":
            raise ValueError(f"formato de horário inválido: '{horario}'. use obrigatoriamente HH:MM (ex: '08:05', '09:30').")

        horas_str, minutos_str = horario.split(":")

        if not (horas_str.isdigit() and minutos_str.isdigit()):
            raise ValueError(f"horário deve conter apenas números no formato HH:MM: '{horario}'.")

        horas = int(horas_str)
        minutos = int(minutos_str)

        if not (0 <= horas <= 23 and 0 <= minutos <= 59):
            raise ValueError(f"horário fora do intervalo válido (00:00 a 23:59): '{horario}'.")

    def inserir(self, horario, id_paciente, dado=None):
        self._validar_horario(horario)
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
                raise ValueError(f"chave duplicada na árvore rubro-negra: {chave_composta}")

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

    def buscar(self, horario, id_paciente):
        self._validar_horario(horario)
        chave_composta = (horario, id_paciente)
        atual = self.raiz

        while atual != self.NIL:
            if chave_composta == atual.chave:
                return atual
            elif chave_composta < atual.chave:
                atual = atual.esq
            else:
                atual = atual.dir

        return None

    def percurso_em_ordem(self):
        resultado = []
        self._em_ordem_recursivo(self.raiz, resultado)
        return resultado

    def _em_ordem_recursivo(self, no, resultado):
        if no != self.NIL:
            self._em_ordem_recursivo(no.esq, resultado)
            resultado.append((no.chave, no.dado))
            self._em_ordem_recursivo(no.dir, resultado)

    def _minimo(self, no):
        while no.esq != self.NIL:
            no = no.esq
        return no

    def _transplantar(self, u, v):
        if u.pai is None:
            self.raiz = v
        elif u == u.pai.esq:
            u.pai.esq = v
        else:
            u.pai.dir = v
        v.pai = u.pai

    def remover(self, horario, id_paciente):
        z = self.buscar(horario, id_paciente)
        if z is None:
            return False

        y = z
        cor_original_y = y.cor

        if z.esq == self.NIL:
            x = z.dir
            self._transplantar(z, z.dir)
        elif z.dir == self.NIL:
            x = z.esq
            self._transplantar(z, z.esq)
        else:
            y = self._minimo(z.dir)
            cor_original_y = y.cor
            x = y.dir

            if y.pai == z:
                x.pai = y
            else:
                self._transplantar(y, y.dir)
                y.dir = z.dir
                y.dir.pai = y

            self._transplantar(z, y)
            y.esq = z.esq
            y.esq.pai = y
            y.cor = z.cor

        if cor_original_y == BLACK:
            self._corrigir_remocao(x)

        return True

    def _corrigir_remocao(self, x):
        while x != self.raiz and x.cor == BLACK:
            if x == x.pai.esq:
                w = x.pai.dir

                if w.cor == RED:
                    w.cor = BLACK
                    x.pai.cor = RED
                    self._rotacao_esquerda(x.pai)
                    w = x.pai.dir

                if w.esq.cor == BLACK and w.dir.cor == BLACK:
                    w.cor = RED
                    x = x.pai
                else:
                    if w.dir.cor == BLACK:
                        w.esq.cor = BLACK
                        w.cor = RED
                        self._rotacao_direita(w)
                        w = x.pai.dir

                    w.cor = x.pai.cor
                    x.pai.cor = BLACK
                    w.dir.cor = BLACK
                    self._rotacao_esquerda(x.pai)
                    x = self.raiz
            else:
                w = x.pai.esq

                if w.cor == RED:
                    w.cor = BLACK
                    x.pai.cor = RED
                    self._rotacao_direita(x.pai)
                    w = x.pai.esq

                if w.dir.cor == BLACK and w.esq.cor == BLACK:
                    w.cor = RED
                    x = x.pai
                else:
                    if w.esq.cor == BLACK:
                        w.dir.cor = BLACK
                        w.cor = RED
                        self._rotacao_esquerda(w)
                        w = x.pai.esq

                    w.cor = x.pai.cor
                    x.pai.cor = BLACK
                    w.esq.cor = BLACK
                    self._rotacao_direita(x.pai)
                    x = self.raiz

        x.cor = BLACK

    def validar_propriedades(self):
        if self.NIL.cor != BLACK:
            raise AssertionError("violação da propriedade 3: folha NIL não é negra.")

        if self.raiz == self.NIL:
            return True

        if self.raiz.cor != BLACK:
            raise AssertionError("violação da propriedade 2: a raiz não é negra.")

        self._validar_no(self.raiz, None, None)
        return True

    def _validar_no(self, no, chave_min, chave_max):
        if no == self.NIL:
            return 1

        if no.cor not in (RED, BLACK):
            raise AssertionError(f"violação da propriedade 1: nó {no.chave} com cor inválida.")

        if (chave_min is not None and no.chave <= chave_min) or (chave_max is not None and no.chave >= chave_max):
            raise AssertionError(f"violação de ordenação ABB no nó {no.chave}.")

        if no.cor == RED:
            if no.esq.cor == RED or no.dir.cor == RED:
                raise AssertionError(f"violação da propriedade 4: nó rubro {no.chave} possui filho rubro.")

        altura_negra_esq = self._validar_no(no.esq, chave_min, no.chave)
        altura_negra_dir = self._validar_no(no.dir, no.chave, chave_max)

        if altura_negra_esq != altura_negra_dir:
            raise AssertionError(
                f"violação da propriedade 5: altura-negra divergente no nó {no.chave} "
                f"(esq={altura_negra_esq}, dir={altura_negra_dir})."
            )

        return altura_negra_esq + (1 if no.cor == BLACK else 0)

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
