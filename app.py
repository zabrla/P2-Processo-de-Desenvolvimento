from datetime import datetime
from pathlib import Path
from sqlite3 import Error as ErroSQLite

import streamlit as st

from sigae.banco import BancoSIGAE, ID_MAXIMO
from sigae.interface import desenhar_arvore
from sigae.sistema import CLASSIFICACOES, ErroSIGAE, SIGAE


def classificacao(prioridade):
    return f"{prioridade} · {CLASSIFICACOES[prioridade]}"


def senha(id_paciente, prioridade):
    prefixo = "P" if prioridade <= 3 else "N"
    return f"{prefixo}-{id_paciente}"


def senha_da_ficha(ficha):
    return senha(ficha.id, ficha.prioridade)


def tabela(fichas):
    if not fichas:
        st.info("Nenhum atendimento nesta lista.")
        return
    st.dataframe(
        [
            {
                "Senha": senha_da_ficha(ficha),
                "Paciente": ficha.nome,
                "Chegada": ficha.horario,
                "Classificação": classificacao(ficha.prioridade),
                "Situação": ficha.status,
                "Consultório": ficha.consultorio,
            }
            for ficha in fichas
        ],
        hide_index=True,
        width="stretch",
    )


def executar(operacao, mensagem, *args):
    try:
        ficha = operacao(*args)
    except (ErroSIGAE, ErroSQLite) as erro:
        st.session_state["erro"] = str(erro)
    else:
        st.session_state["sucesso"] = (
            f"{mensagem} {senha_da_ficha(ficha)}." if ficha else mensagem
        )


def consultorios(banco, sistema):
    proximo = sistema.proximo_da_fila()
    for numero, (coluna, ficha) in enumerate(
        zip(st.columns(2), sistema.em_atendimento()), start=1
    ):
        with coluna, st.container(border=True, key=f"consultorio_{numero}"):
            st.subheader(f"Consultório {numero}")
            if ficha:
                st.markdown(":orange-background[Em atendimento]")
                st.metric("Senha em atendimento", senha_da_ficha(ficha), label_visibility="collapsed")
                st.text(ficha.nome)
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
                    f"Chamar {senha_da_ficha(proximo)}" if proximo else "Chamar próximo",
                    key=f"chamar_{numero}",
                    on_click=executar,
                    args=(banco.chamar, f"Consultório {numero} chamou", numero,
                          proximo.id if proximo else None),
                    disabled=proximo is None,
                    type="primary",
                    width="stretch",
                )


def cadastro(banco):
    with st.form("cadastro"):
        nome = st.text_input("Nome completo", max_chars=90)
        chegada, risco = st.columns(2)
        horario = chegada.time_input("Horário de chegada", datetime.now().time(), step=60)
        prioridade = risco.selectbox(
            "Classificação", range(1, 6), index=2, format_func=classificacao
        )
        numero = st.text_input("Número manual (opcional)", max_chars=19)
        if not st.form_submit_button("Registrar entrada", type="primary"):
            return

    try:
        id_paciente = int(numero) if numero.strip() else None
    except ValueError:
        st.error("Informe um número de atendimento inteiro positivo.")
        return
    executar(banco.cadastrar, "Entrada registrada com a senha", nome,
             horario.strftime("%H:%M"), prioridade, id_paciente)
    st.rerun()


def consultar(sistema, codigo):
    prefixo, separador, numero = codigo.strip().upper().partition("-")
    if prefixo not in ("P", "N") or not separador or not numero.isascii() or not numero.isdecimal():
        raise ErroSIGAE("Digite a senha no formato P-1000 ou N-1000.")
    id_paciente = int(numero)
    if not 1 <= id_paciente <= ID_MAXIMO:
        raise ErroSIGAE("Número de atendimento fora do intervalo permitido.")
    ficha = sistema.localizar(id_paciente)
    if senha_da_ficha(ficha) != f"{prefixo}-{id_paciente}":
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
    tabela(fichas)
    if not fichas:
        return
    with st.form("alterar_fila"):
        ficha = st.selectbox("Senha para alterar", fichas, format_func=senha_da_ficha)
        prioridade = st.selectbox("Nova classificação", range(1, 6), format_func=classificacao)
        reclassificar = st.form_submit_button("Reclassificar")
        cancelar = st.form_submit_button("Cancelar atendimento")
    if reclassificar:
        executar(banco.reclassificar, "Classificação atualizada. Senha", ficha.id, prioridade)
        st.rerun()
    if cancelar:
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
        st.caption("P · Prioridades 1 a 3\n\nN · Prioridades 4 e 5")
        st.button("Atualizar dados", width="stretch")

    st.title(pagina)
    if erro := st.session_state.pop("erro", None):
        st.error(erro)
    if sucesso := st.session_state.pop("sucesso", None):
        st.success(sucesso)

    if pagina == "Visão geral":
        proximo = sistema.proximo_da_fila()
        with st.container(key="indicadores"):
            contagem, chamada, concluidos = st.columns(3)
            contagem.metric("Aguardando", sistema.aguardando(), border=True)
            chamada.metric("Próxima senha", senha_da_ficha(proximo) if proximo else "—", border=True)
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
