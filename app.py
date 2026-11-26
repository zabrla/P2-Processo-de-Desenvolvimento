from datetime import datetime
from html import escape
from pathlib import Path
from sqlite3 import Error as ErroSQLite

import streamlit as st

from sigae.banco import BancoSIGAE, ID_MAXIMO
from sigae.interface import desenhar_arvore
from sigae.sistema import CLASSIFICACOES, NORMAL, ErroSIGAE, SIGAE, senha


def classificacao(prioridade):
    return CLASSIFICACOES[prioridade]


def tabela(fichas):
    if not fichas:
        st.info("Nenhum atendimento nesta lista.")
        return

    tamanho = 10
    if len(fichas) > tamanho:
        total_paginas = (len(fichas) + tamanho - 1) // tamanho
        pagina = st.selectbox("Página de resultados", range(1, total_paginas + 1))
        inicio = (pagina - 1) * tamanho
        fichas = fichas[inicio : inicio + tamanho]

    with st.container(key="lista_desktop"):
        st.dataframe(
            [
                {
                    "Senha": ficha.senha,
                    "Paciente": ficha.nome,
                    "Chegada": ficha.horario,
                    "Classificação": classificacao(ficha.prioridade),
                    "Situação": ficha.status,
                    "Consultório": ficha.consultorio,
                }
                for ficha in fichas
            ],
            column_config={"Consultório": st.column_config.NumberColumn(format="%d")},
            hide_index=True,
            width="stretch",
        )

    cartoes = []
    for ficha in fichas:
        consultorio = f" · Consultório {ficha.consultorio}" if ficha.consultorio else ""
        cartoes.append(
            '<li class="ficha-mobile">'
            f'<strong>{ficha.senha}</strong>'
            f'<span class="ficha-nome">{escape(ficha.nome)}</span>'
            f'<span>Chegada {escape(ficha.horario)} · {classificacao(ficha.prioridade)}</span>'
            f'<span>{escape(ficha.status)}{consultorio}</span>'
            '</li>'
        )
    st.html(f'<ul class="fichas-mobile" aria-label="Atendimentos">{"".join(cartoes)}</ul>')


def executar(operacao, mensagem, *args):
    try:
        ficha = operacao(*args)
    except (ErroSIGAE, ErroSQLite) as erro:
        st.session_state["erro"] = str(erro)
        return False
    else:
        st.session_state["sucesso"] = (
            f"{mensagem} {ficha.senha}." if ficha else mensagem
        )
        return True


def consultorios(banco, sistema):
    proximo = sistema.proximo_da_fila()
    for numero, (coluna, ficha) in enumerate(
        zip(st.columns(2), sistema.em_atendimento()), start=1
    ):
        with coluna, st.container(border=True, key=f"consultorio_{numero}"):
            st.subheader(f"Consultório {numero}")
            if ficha:
                st.markdown(":orange-background[Em atendimento]")
                st.metric("Senha em atendimento", ficha.senha, label_visibility="collapsed")
                st.html(f'<div class="paciente-em-atendimento">{escape(ficha.nome)}</div>')
                st.button(
                    "Concluir atendimento",
                    key=f"concluir_{numero}_{ficha.id}",
                    on_click=executar,
                    args=(banco.concluir, "Atendimento concluído", numero, ficha.id),
                    width="stretch",
                )
            else:
                st.markdown(":green-background[Livre]")
                st.button(
                    f"Chamar {proximo.senha}" if proximo else "Chamar próximo",
                    key=f"chamar_{numero}",
                    on_click=executar,
                    args=(banco.chamar, f"Consultório {numero} chamou", numero,
                          proximo.id if proximo else None,
                          proximo.prioridade if proximo else None),
                    disabled=proximo is None,
                    type="primary",
                    width="stretch",
                )


def cadastro(banco):
    versao = st.session_state.get("versao_cadastro", 0)
    with st.form(f"cadastro_{versao}"):
        nome = st.text_input("Nome completo", max_chars=90, key=f"nome_{versao}")
        chegada, risco = st.columns(2)
        horario = chegada.time_input(
            "Horário de chegada", datetime.now().time(), step=60, key=f"horario_{versao}"
        )
        prioridade = risco.selectbox(
            "Classificação", list(CLASSIFICACOES), index=NORMAL - 1,
            format_func=classificacao, key=f"risco_{versao}"
        )
        numero = st.text_input("Número manual (opcional)", max_chars=19, key=f"numero_{versao}")
        if not st.form_submit_button("Registrar entrada", type="primary", width="stretch"):
            return

    try:
        id_paciente = int(numero) if numero.strip() else None
    except ValueError:
        st.error("Informe um número de atendimento inteiro positivo.")
        return
    gravou = executar(
        banco.cadastrar, "Entrada registrada com a senha",
        nome, horario.strftime("%H:%M"), prioridade, id_paciente,
    )
    if gravou:
        st.session_state["versao_cadastro"] = versao + 1
    st.rerun()


def consultar(sistema, codigo):
    prefixo, separador, numero = codigo.strip().upper().partition("-")
    if prefixo not in ("P", "N") or not separador or not numero.isascii() or not numero.isdecimal():
        raise ErroSIGAE("Digite a senha no formato P-1000 ou N-1000.")
    id_paciente = int(numero)
    if not 1 <= id_paciente <= ID_MAXIMO:
        raise ErroSIGAE("Número de atendimento fora do intervalo permitido.")
    ficha = sistema.localizar(id_paciente)
    if ficha.senha != f"{prefixo}-{id_paciente}":
        raise ErroSIGAE("O prefixo informado não corresponde à classificação atual da ficha.")
    return ficha


def pacientes(sistema):
    codigo = st.text_input("Consultar senha", placeholder="P-1000 ou N-1000", max_chars=22)
    if codigo.strip():
        try:
            tabela([consultar(sistema, codigo)])
        except ErroSIGAE as erro:
            st.error(str(erro))
        return
    tabela([sistema.localizar(id_paciente) for id_paciente in sorted(sistema.fichas.chaves())])


def fila(banco, fichas):
    if not fichas:
        tabela(fichas)
        return
    por_senha = {ficha.senha: ficha for ficha in fichas}
    codigo = st.selectbox(
        "Senha para alterar", list(por_senha), index=None,
        placeholder="Selecione uma senha",
    )
    if codigo is None:
        tabela(fichas)
        return
    ficha = por_senha[codigo]
    with st.form(f"alterar_fila_{codigo}"):
        prioridade = st.selectbox(
            "Nova classificação", list(CLASSIFICACOES), index=ficha.prioridade - 1,
            format_func=classificacao,
        )
        reclassificar = st.form_submit_button("Reclassificar", width="stretch")
        confirmar = st.checkbox(f"Confirmo o cancelamento de {codigo}")
        cancelar = st.form_submit_button("Cancelar atendimento", width="stretch")
    tabela(fichas)
    if reclassificar:
        executar(banco.reclassificar, "Classificação atualizada. Senha", ficha.id, prioridade)
        st.rerun()
    if cancelar:
        if not confirmar:
            st.warning(f"Confirme o cancelamento de {codigo} antes de enviar.")
            return
        executar(banco.cancelar, "Atendimento cancelado", ficha.id)
        st.rerun()


def diagnostico(banco, sistema):
    st.success("Árvore, heap, hash e estados das fichas validados.")
    arvore, heap, hash_ = st.tabs(["Árvore Rubro-Negra", "Min-Heap", "Tabela Hash"])
    linhas = desenhar_arvore(sistema.arvore, sistema.arvore.raiz, linhas=[])
    arvore.code("\n".join(linhas) or "(vazia)", language=None)
    niveis = []
    inicio, tamanho = 0, 1
    while inicio < len(sistema.heap.v):
        pacientes_no_nivel = sistema.heap.v[inicio : inicio + tamanho]
        niveis.append("  ".join(senha(p.id, p.prioridade) for p in pacientes_no_nivel))
        inicio += tamanho
        tamanho *= 2
    heap.code("\n".join(niveis) or "(vazio)", language=None)
    hash_.code(sistema.espera.exibir(), language=None)

    if len(sistema.fichas) == 0:
        st.subheader("Cenários de exemplo")
        cenarios = {"Padrão": SIGAE.CENARIO_PADRAO, "Colisões na hash": SIGAE.CENARIO_COLISAO}
        selecionado = st.selectbox("Cenário", list(cenarios))
        if st.button("Carregar exemplo"):
            executar(banco.carregar_exemplos, "Cenário carregado.", cenarios[selecionado])
            st.rerun()


def main():
    st.set_page_config(page_title="SIGAE | Central de atendimento", layout="wide")
    st.html(Path(__file__).with_name("estilo.css"))
    try:
        banco = BancoSIGAE()
        sistema = banco.carregar()
    except (ErroSIGAE, ErroSQLite, AssertionError) as erro:
        st.error(f"Falha ao abrir a base do SIGAE. {erro}")
        return

    with st.sidebar:
        st.title("SIGAE")
        pagina = st.radio(
            "Navegação",
            ["Visão geral", "Consultórios", "Novo paciente", "Fila de espera",
             "Pacientes", "Chegadas", "Histórico", "Estruturas"],
            key="navegacao",
        )
        st.caption("P · Prioridade\n\nN · Normal")
        st.button("Atualizar dados", width="stretch")

    st.title(pagina)
    if erro := st.session_state.pop("erro", None):
        st.error(erro)
    if sucesso := st.session_state.pop("sucesso", None):
        st.success(sucesso)

    if pagina == "Visão geral":
        proximo = sistema.proximo_da_fila()
        with st.container(key="indicadores"):
            chamada, contagem, concluidos = st.columns([2, 1, 1])
            chamada.metric("Próxima senha", proximo.senha if proximo else "—", border=True)
            contagem.metric("Aguardando", sistema.aguardando(), border=True)
            concluidos.metric("Concluídos", sistema.concluidos(), border=True)
        consultorios(banco, sistema)
        st.subheader("Próximos atendimentos")
        tabela(sorted(sistema.lista_por_chegada(), key=lambda ficha: ficha.paciente.chave())[:5])
    elif pagina == "Consultórios":
        consultorios(banco, sistema)
    elif pagina == "Novo paciente":
        cadastro(banco)
    elif pagina == "Fila de espera":
        fila(banco, sorted(sistema.lista_por_chegada(), key=lambda ficha: ficha.paciente.chave()))
    elif pagina == "Pacientes":
        pacientes(sistema)
    elif pagina == "Chegadas":
        tabela(sistema.lista_por_chegada())
    elif pagina == "Histórico":
        tabela(sistema.fichas_do_historico())
    elif pagina == "Estruturas":
        diagnostico(banco, sistema)


if __name__ == "__main__":
    main()
