from textwrap import wrap

from matplotlib.figure import Figure

from sigae.estruturas.arvore_rubro_negra import RED

NIVEIS_VISIVEIS = 4
AZUL = "#3945be"
VERDE = "#087454"
VERMELHO = "#b42345"
NEGRO = "#18233a"
LINHA = "#a6b0c4"
FUNDO = "#f5f7fb"


def _grafo(raiz, filhos, aparencia):
    posicoes = {}
    arestas = []

    def posicionar(no, nivel):
        esquerda, direita = filhos(no)
        if nivel < NIVEIS_VISIVEIS - 1 and esquerda is not None:
            posicionar(esquerda, nivel + 1)
            arestas.append((no, esquerda))
        posicoes[no] = (len(posicoes), -nivel)
        if nivel < NIVEIS_VISIVEIS - 1 and direita is not None:
            posicionar(direita, nivel + 1)
            arestas.append((no, direita))

    posicionar(raiz, 0)
    profundidade = -min(y for _, y in posicoes.values())
    largura = min(9, max(4, len(posicoes) * 0.85))
    figura = Figure(figsize=(largura, 1.2 + 0.92 * profundidade), facecolor=FUNDO)
    eixo = figura.add_axes((0.04, 0.03, 0.92, 0.94))
    eixo.set_axis_off()
    eixo.set_xlim(-0.75, len(posicoes) - 0.25)
    eixo.set_ylim(-profundidade - 0.58, 0.48)

    for pai, filho in arestas:
        x_pai, y_pai = posicoes[pai]
        x_filho, y_filho = posicoes[filho]
        eixo.plot((x_pai, x_filho), (y_pai, y_filho), color=LINHA, linewidth=1.5, zorder=1)

    for no, (x, y) in posicoes.items():
        rotulo, cor = aparencia(no)
        if y == 1 - NIVEIS_VISIVEIS and any(filho is not None for filho in filhos(no)):
            rotulo += "\n↓"
        eixo.text(
            x, y, rotulo, ha="center", va="center", color="white", fontsize=9,
            bbox={"boxstyle": "round,pad=0.35", "facecolor": cor, "edgecolor": "none"},
            zorder=2,
        )

    return figura


def arvore_rubro_negra(arvore, raiz):
    def filhos(no):
        return tuple(filho if filho is not arvore.NIL else None for filho in (no.esq, no.dir))

    def aparencia(no):
        horario, numero = no.chave
        vermelho = no.cor == RED
        return f"#{numero} · {'V' if vermelho else 'N'}\n{horario}", VERMELHO if vermelho else NEGRO

    return _grafo(raiz, filhos, aparencia)


def heap_binario(elementos, raiz, rotulo, cor):
    def filhos(posicao):
        candidatos = (2 * posicao + 1, 2 * posicao + 2)
        return tuple(filho if filho < len(elementos) else None for filho in candidatos)

    return _grafo(raiz, filhos, lambda posicao: (rotulo(elementos[posicao]), cor))


def buckets_hash(buckets, inicio):
    linhas = [
        "\n".join(wrap(" → ".join(map(str, ids)) or "—", width=33))
        for ids in buckets
    ]
    alturas = [linha.count("\n") + 1.4 for linha in linhas]
    total = sum(alturas)
    figura = Figure(figsize=(4.8, 0.38 * total + 0.18), facecolor=FUNDO)
    eixo = figura.add_axes((0.04, 0.03, 0.92, 0.94))
    eixo.set_axis_off()
    eixo.set(xlim=(0, 1), ylim=(total, 0))
    topo = 0
    for indice, (linha, altura, ids) in enumerate(zip(linhas, alturas, buckets), start=inicio):
        meio = topo + altura / 2
        eixo.axhspan(topo, topo + altura, color="#eef0ff" if indice % 2 == 0 else "#ffffff")
        eixo.text(0.04, meio, f"[{indice}]", va="center", color=NEGRO, fontsize=10, weight="bold")
        eixo.text(0.24, meio, linha, va="center", color=AZUL if len(ids) > 1 else NEGRO, fontsize=10)
        topo += altura

    return figura
