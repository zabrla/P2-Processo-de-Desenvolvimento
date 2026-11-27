from datetime import datetime
from html import escape
from pathlib import Path
from sqlite3 import Error as ErroSQLite

import streamlit as st

from sigae.banco import BancoSIGAE, ID_MAXIMO
from sigae.graficos import AZUL, VERDE, arvore_rubro_negra, buckets_hash, heap_binario
from sigae.sistema import AGUARDANDO, CANCELADO, CLASSIFICACOES, EM_ATENDIMENTO, NORMAL, ErroSIGAE, SIGAE, senha


def classificacao(prioridade):
    return f"{prioridade} · {CLASSIFICACOES[prioridade]}"


def horario_inicio(ficha):
    return (
        datetime.fromisoformat(ficha.inicio).strftime("%d/%m/%Y às %H:%M:%S")
        if ficha.inicio else "Sem registro"
    )


def tabela(fichas, sistema):
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
                    "Médico": sistema.localizar_medico(ficha.medico_id).nome if ficha.medico_id else None,
                    "Início": horario_inicio(ficha) if ficha.medico_id else None,
                }
                for ficha in fichas
            ],
            hide_index=True,
            width="stretch",
        )

    cartoes = []
    for ficha in fichas:
        vinculo = ""
        if ficha.medico_id:
            medico = sistema.localizar_medico(ficha.medico_id)
            vinculo = f'<span>Médico: {escape(medico.nome)} · Início: {horario_inicio(ficha)}</span>'
        cartoes.append(
            '<li class="ficha-mobile">'
            f'<strong>{ficha.senha}</strong>'
            f'<span class="ficha-nome">{escape(ficha.nome)}</span>'
            f'<span>Chegada {escape(ficha.horario)} · {classificacao(ficha.prioridade)}</span>'
            f'<span>{escape(ficha.status)}</span>'
            f'{vinculo}'
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


def chamar_proximo(banco, sistema):
    proximo = sistema.proximo_da_fila()
    disponivel = sistema.heap_medicos.topo()
    if proximo is None:
        st.info("Nenhum paciente aguardando.")
        return
    if disponivel is None:
        st.info("Nenhum médico disponível. O paciente permanece na fila.")

    st.button(
        f"Chamar {proximo.senha}",
        type="primary",
        width="stretch",
        disabled=disponivel is None,
        on_click=executar,
        args=(banco.chamar, "Senha chamada:", proximo.id, proximo.prioridade),
    )


def atendimentos(banco, sistema):
    chamar_proximo(banco, sistema)
    st.subheader("Em andamento")
    fichas = sistema.em_atendimento()
    if not fichas:
        st.info("Nenhum atendimento em andamento.")
        return
    for ficha in fichas:
        medico = sistema.localizar_medico(ficha.medico_id)
        with st.container(border=True, key=f"consultorio_{ficha.id}"):
            st.subheader(ficha.senha)
            st.markdown(":orange-background[Em atendimento]")
            st.html(
                f'<div class="paciente-em-atendimento"><strong>{escape(ficha.nome)}</strong><br>'
                f'Médico: {escape(medico.nome)} · #{medico.id}<br>'
                f'Início: {horario_inicio(ficha)}</div>'
            )
            st.button(
                "Concluir atendimento", key=f"concluir_{ficha.id}",
                on_click=executar, args=(banco.concluir, "Atendimento concluído", ficha.id),
                width="stretch",
            )
            with st.expander("Cancelar atendimento"):
                confirmou = st.checkbox(f"Confirmo o cancelamento de {ficha.senha}", key=f"confirma_{ficha.id}")
                st.button(
                    "Confirmar cancelamento", key=f"cancelar_{ficha.id}", disabled=not confirmou,
                    on_click=executar,
                    args=(banco.cancelar, "Atendimento cancelado", ficha.id, EM_ATENDIMENTO),
                    width="stretch",
                )


def medicos(banco, sistema):
    st.subheader("Cadastrar médico clínico")
    versao = st.session_state.get("versao_medico", 0)
    with st.form(f"cadastro_medico_{versao}"):
        nome = st.text_input("Nome do médico", max_chars=90, key=f"medico_nome_{versao}")
        registro = st.text_input("Registro profissional fictício", max_chars=24, key=f"medico_registro_{versao}")
        enviado = st.form_submit_button("Cadastrar médico", type="primary", width="stretch")
    if enviado:
        try:
            medico = banco.cadastrar_medico(nome, registro)
        except (ErroSIGAE, ErroSQLite) as erro:
            st.error(str(erro))
        else:
            st.session_state["sucesso"] = f"Médico #{medico.id} cadastrado."
            st.session_state["versao_medico"] = versao + 1
            st.rerun()

    st.subheader("Equipe clínica")
    equipe = sistema.listar_medicos()
    if not equipe:
        st.info("Nenhum médico cadastrado.")
        return
    escolhido = st.selectbox(
        "Consultar médico", [medico.id for medico in equipe], index=None,
        format_func=lambda numero: f"#{numero} · {sistema.localizar_medico(numero).nome}",
        placeholder="Todos os médicos",
    )
    if escolhido is not None:
        equipe = [sistema.localizar_medico(escolhido)]
    for medico in equipe:
        with st.container(border=True):
            st.html(f'<strong>#{medico.id} · {escape(medico.nome)}</strong><br>{escape(medico.registro)}')
            st.markdown(
                ":green-background[Disponível]" if medico.ficha_id is None else ":orange-background[Em atendimento]"
            )
            st.write(f"Atendimentos concluídos: {medico.concluidos}")


def historico(sistema):
    fichas = sistema.fichas_do_historico()
    equipe = sistema.listar_medicos()
    escolhido = st.selectbox(
        "Filtrar por médico", [medico.id for medico in equipe], index=None,
        format_func=lambda numero: f"#{numero} · {sistema.localizar_medico(numero).nome}",
        placeholder="Todos os médicos",
    )
    if escolhido is not None:
        fichas = [ficha for ficha in fichas if ficha.medico_id == escolhido]
    tabela(fichas, sistema)


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
        if not st.form_submit_button("Registrar entrada", type="primary", width="stretch"):
            return

    gravou = executar(
        banco.cadastrar, "Entrada registrada com a senha",
        nome, horario.strftime("%H:%M"), prioridade,
    )
    if gravou:
        st.session_state["versao_cadastro"] = versao + 1
    st.rerun()


def consultar(sistema, codigo):
    codigo = codigo.strip().upper()
    prefixo, separador, numero = codigo.partition("-")
    if not separador:
        prefixo, numero = "", codigo
    if prefixo not in ("", "P", "N") or (separador and not prefixo) or not numero.isascii() or not numero.isdecimal():
        raise ErroSIGAE("Informe um ID numérico ou uma senha como P-1000 ou N-1000.")
    id_paciente = int(numero)
    if not 1 <= id_paciente <= ID_MAXIMO:
        raise ErroSIGAE("Número de atendimento fora do intervalo permitido.")
    ficha = sistema.localizar(id_paciente)
    if prefixo and ficha.senha != f"{prefixo}-{id_paciente}":
        raise ErroSIGAE("O prefixo informado não corresponde à classificação atual da ficha.")
    return ficha


def pacientes(sistema):
    codigo = st.text_input("Consultar por ID ou senha", placeholder="1000, P-1000 ou N-1000", max_chars=22)
    if codigo.strip():
        try:
            tabela([consultar(sistema, codigo)], sistema)
        except ErroSIGAE as erro:
            st.error(str(erro))
        return
    tabela([sistema.localizar(id_paciente) for id_paciente in sorted(sistema.fichas.chaves())], sistema)


def fila(banco, sistema):
    fichas = sorted(sistema.lista_por_chegada(), key=lambda ficha: ficha.paciente.chave())
    if not fichas:
        tabela(fichas, sistema)
        return
    id_paciente = st.selectbox(
        "Senha para alterar", [ficha.id for ficha in fichas], index=None,
        format_func=lambda numero: sistema.localizar(numero).senha,
        placeholder="Selecione uma senha",
    )
    if id_paciente is None:
        tabela(fichas, sistema)
        return
    ficha = sistema.localizar(id_paciente)
    codigo = ficha.senha
    with st.form(f"alterar_fila_{codigo}"):
        prioridade = st.selectbox(
            "Nova classificação", list(CLASSIFICACOES), index=ficha.prioridade - 1,
            format_func=classificacao,
        )
        reclassificar = st.form_submit_button("Reclassificar", width="stretch")
        confirmar = st.checkbox(f"Confirmo o cancelamento de {codigo}")
        cancelar = st.form_submit_button("Cancelar atendimento", width="stretch")
    tabela(fichas, sistema)
    if reclassificar:
        executar(banco.reclassificar, "Classificação atualizada. Senha", ficha.id, prioridade)
        st.rerun()
    if cancelar:
        if not confirmar:
            st.warning(f"Confirme o cancelamento de {codigo} antes de enviar.")
            return
        executar(banco.cancelar, "Atendimento cancelado", ficha.id, AGUARDANDO)
        st.rerun()


def mostrar_arvore(arvore):
    raiz = arvore.raiz
    if raiz is arvore.NIL:
        st.info("A árvore está vazia.")
        return

    chaves = [chave for chave, _ in arvore.percurso_em_ordem()]
    if len(chaves) > 7:
        foco = st.selectbox(
            "Foco da árvore", [None, *chaves],
            format_func=lambda chave: "Raiz da árvore" if chave is None else f"#{chave[1]} · {chave[0]}",
        )
        if foco is not None:
            raiz = arvore.buscar(*foco)
    st.caption("V indica vermelho e N indica negro. A seta ↓ indica descendentes fora da vista.")
    st.pyplot(
        arvore_rubro_negra(arvore, raiz), clear_figure=True,
        alt=f"Árvore rubro-negra com foco na ficha #{raiz.chave[1]}.",
    )


def mostrar_heap(heap, rotulo, cor, titulo, vazio):
    elementos = heap.v
    if not elementos:
        st.info(vazio)
        return

    raiz = 0
    if len(elementos) > 7:
        foco = st.selectbox(
            "Foco do heap", [None, *(elemento.id for elemento in elementos)],
            format_func=lambda codigo: "Raiz do heap" if codigo is None
            else rotulo(heap.buscar(codigo)).replace("\n", " · "),
        )
        if foco is not None:
            raiz = heap.posicao(foco)
        st.caption("A seta ↓ indica descendentes fora da vista.")

    descricao = rotulo(elementos[raiz]).replace("\n", " · ")
    st.pyplot(
        heap_binario(elementos, raiz, rotulo, cor), clear_figure=True,
        alt=f"{titulo}. Foco: {descricao}.",
    )


def mostrar_hash(tabela_hash):
    capacidade = tabela_hash.capacidade()
    registros = len(tabela_hash)
    st.caption(
        f"Capacidade {capacidade} · {registros} registros · "
        f"{tabela_hash.colisoes()} colisões · Carga {tabela_hash.fator_carga():.0%}"
    )
    if not registros:
        st.info("Nenhum paciente indexado na fila de espera.")
        return

    tamanho = 8
    inicios = range(0, capacidade, tamanho)
    buckets = list(tabela_hash.ids_por_bucket())
    primeiro_ocupado = next(indice for indice, ids in enumerate(buckets) if ids)
    inicio = st.selectbox(
        "Faixa de buckets", inicios, index=primeiro_ocupado // tamanho,
        format_func=lambda posicao: f"{posicao} a {min(posicao + tamanho, capacidade) - 1}",
    )
    fim = min(inicio + tamanho, capacidade)
    st.pyplot(
        buckets_hash(buckets[inicio:fim], inicio), clear_figure=True,
        alt=f"Buckets {inicio} a {fim - 1} da hash de pacientes em espera.",
    )


def diagnostico(banco, sistema):
    st.success("Árvore, dois heaps, hashes e vínculos validados.")
    arvore, pacientes, medicos, hash_ = st.tabs(
        ["Árvore Rubro-Negra", "Heap de pacientes", "Heap de médicos", "Tabela Hash"],
        key="estrutura_selecionada", on_change="rerun",
    )
    if arvore.open:
        with arvore:
            mostrar_arvore(sistema.arvore)
    elif pacientes.open:
        with pacientes:
            st.caption("A raiz é a próxima chamada. Cada nó mostra a senha e o nível de risco.")
            mostrar_heap(
                sistema.heap, lambda paciente: f"{senha(paciente.id, paciente.prioridade)}\nRisco {paciente.prioridade}",
                AZUL, "Heap de pacientes", "Nenhum paciente aguardando.",
            )
    elif medicos.open:
        with medicos:
            st.caption("Cada nó mostra o ID do médico e a chave (concluídos, última atribuição, ID).")
            mostrar_heap(
                sistema.heap_medicos, lambda medico: f"#{medico.id}\n{medico.chave()}",
                VERDE, "Heap de médicos disponíveis", "Nenhum médico disponível.",
            )
    elif hash_.open:
        with hash_:
            mostrar_hash(sistema.espera)

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
            ["Visão geral", "Novo paciente", "Pacientes", "Triagem / Fila",
             "Médicos", "Atendimentos", "Histórico", "Chegadas", "Estruturas"],
            key="navegacao",
        )
        st.caption("P · Riscos 1 a 3\n\nN · Riscos 4 e 5")
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
        em_curso, cancelados = st.columns(2)
        em_curso.metric("Em atendimento", len(sistema.em_atendimento()))
        cancelados.metric(
            "Cancelados", sum(ficha.status == CANCELADO for ficha in sistema.fichas_do_historico())
        )
        chamar_proximo(banco, sistema)
        st.subheader("Próximos atendimentos")
        tabela(sorted(sistema.lista_por_chegada(), key=lambda ficha: ficha.paciente.chave())[:5], sistema)
    elif pagina == "Atendimentos":
        atendimentos(banco, sistema)
    elif pagina == "Médicos":
        medicos(banco, sistema)
    elif pagina == "Novo paciente":
        cadastro(banco)
    elif pagina == "Triagem / Fila":
        fila(banco, sistema)
    elif pagina == "Pacientes":
        pacientes(sistema)
    elif pagina == "Chegadas":
        tabela(sistema.lista_por_chegada(), sistema)
    elif pagina == "Histórico":
        historico(sistema)
    elif pagina == "Estruturas":
        diagnostico(banco, sistema)


if __name__ == "__main__":
    main()
