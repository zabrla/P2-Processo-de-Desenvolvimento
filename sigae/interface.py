from datetime import datetime

from sigae.estruturas.arvore_rubro_negra import RED
from sigae.sistema import CLASSIFICACOES, NORMAL, ErroIntegridade, ErroSIGAE, SIGAE, senha


def ler_texto(pergunta, padrao=None):
    sufixo = f" [{padrao}]" if padrao is not None else ""
    resposta = input(f"{pergunta}{sufixo}: ").strip()
    return resposta if resposta else padrao


def ler_inteiro(pergunta, minimo=None, maximo=None, padrao=None, opcional=False):
    while True:
        resposta = ler_texto(pergunta, padrao)
        if resposta is None:
            if opcional:
                return None
            print("  Campo obrigatório.")
            continue
        try:
            valor = int(resposta)
        except (TypeError, ValueError):
            print("  Digite um número inteiro.")
            continue
        if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
            print(f"  Digite um valor entre {minimo} e {maximo}.")
            continue
        return valor


def mostrar_classificacoes():
    for numero, categoria in CLASSIFICACOES.items():
        print(f"  {numero} · {categoria}")


def painel(sistema):
    proximo = sistema.proximo_da_fila()
    texto_proximo = f"{proximo.senha} · {proximo.nome}" if proximo else "—"
    print("=" * 64)
    print("  SIGAE · Central de operações")
    print("=" * 64)
    print(f"  Aguardando: {sistema.aguardando()}    Próximo da fila: {texto_proximo}    "
          f"Concluídos: {sistema.concluidos()}")
    for medico in sistema.listar_medicos():
        situacao = sistema.localizar(medico.ficha_id).senha if medico.ficha_id else medico.status
        print(f"  Médico {medico.id} · {medico.nome}: {situacao} ({medico.concluidos} concluídos)")
    hash_ = sistema.espera
    print(f"  Hash: capacidade {hash_.capacidade()} · carga {hash_.fator_carga():.0%} · "
          f"colisões {hash_.colisoes()}")
    print("-" * 64)


MENU = """
   1. Registrar entrada              7. Concluir atendimento
   2. Consultar ID                    8. Histórico
   3. Reclassificar                   9. Validar índices
   4. Cancelar                       10. Ver estruturas
   5. Lista por chegada              11. Carregar cenário
   6. Chamar próximo da fila         12. Cadastrar médico
   0. Sair                          13. Consultar médico
"""



def registrar(sistema):
    nome = ler_texto("Nome do paciente")
    horario = ler_texto("Hora de chegada (HH:MM)", datetime.now().strftime("%H:%M"))
    mostrar_classificacoes()
    prioridade = ler_inteiro("Classificação", 1, NORMAL, NORMAL)
    ficha = sistema.cadastrar(nome, horario, prioridade)
    return f"Entrada registrada: {ficha.senha} {ficha.nome} · {CLASSIFICACOES[ficha.prioridade]}."


def consultar(sistema):
    id_paciente = ler_inteiro("Nº de atendimento", 1)
    ficha = sistema.localizar(id_paciente)
    indice = sistema.espera._hash(id_paciente) if sistema.espera.contem(id_paciente) else None
    extra = f" · bucket {indice} da Hash" if indice is not None else ""
    return f"Hash: {ficha.resumo()}{extra}."


def reclassificar(sistema):
    id_paciente = ler_inteiro("Nº de atendimento", 1)
    mostrar_classificacoes()
    nova = ler_inteiro("Nova classificação", 1, NORMAL)
    ficha, antiga = sistema.reclassificar(id_paciente, nova)
    proximo = sistema.proximo_da_fila()
    return (f"{ficha.senha} {ficha.nome}: {CLASSIFICACOES[antiga]} → {CLASSIFICACOES[nova]}. "
            f"Raiz do Heap agora: {proximo.senha} {proximo.nome}.")


def cancelar(sistema):
    id_paciente = ler_inteiro("Nº de atendimento", 1)
    ficha = sistema.cancelar(id_paciente)
    return f"Atendimento {ficha.senha} cancelado; encerramento registrado."


def chamar(sistema):
    ficha = sistema.chamar_proximo()
    medico = sistema.localizar_medico(ficha.medico_id)
    return f"{medico.nome} chamou {ficha.senha} · {ficha.nome}."


def concluir(sistema):
    ocupados = sistema.em_atendimento()
    if not ocupados:
        raise ErroSIGAE("Nenhum paciente está em atendimento.")
    id_paciente = ocupados[0].id if len(ocupados) == 1 else ler_inteiro("Nº de atendimento", 1)
    ficha = sistema.concluir(id_paciente)
    return f"Médico {ficha.medico_id} concluiu o atendimento de {ficha.senha} {ficha.nome}."


def listar(sistema):
    fichas = sistema.lista_por_chegada()
    if not fichas:
        return "Fila de espera vazia."
    print("\n  Ordem de chegada (percurso em ordem da Rubro-Negra):")
    for posicao, ficha in enumerate(fichas, start=1):
        print(f"  {posicao:>2}. {ficha.horario}  {ficha.senha} · {ficha.nome}")
    return f"{len(fichas)} paciente(s) aguardando."


def historico(sistema):
    fichas = sistema.fichas_do_historico()
    if not fichas:
        return "Nenhum encerramento ainda."
    print("\n  Histórico (mais recente primeiro):")
    for ficha in fichas:
        print(f"  {ficha.senha} {ficha.nome} — {ficha.status}"
              + (f" (médico {ficha.medico_id})" if ficha.medico_id else ""))
    return f"{len(fichas)} registro(s) no histórico."


def cadastrar_medico(sistema):
    nome = ler_texto("Nome do médico", "")
    registro = ler_texto("Registro profissional fictício", "")
    medico = sistema.cadastrar_medico(nome, registro)
    return f"Médico #{medico.id} cadastrado: {medico.nome} · {medico.registro}."


def consultar_medico(sistema):
    medico = sistema.localizar_medico(ler_inteiro("ID do médico", 1))
    resumo = (
        f"Médico #{medico.id} · {medico.nome} · {medico.registro} · "
        f"{medico.status} · {medico.concluidos} atendimento(s) concluído(s)"
    )
    if medico.ficha_id is not None:
        ficha = sistema.localizar(medico.ficha_id)
        resumo += f" · Ficha {ficha.senha}"
    return resumo


def validar(sistema):
    sistema.validar()
    return "Árvore, heaps, hashes e vínculos de atendimento validados."


def desenhar_arvore(arvore, no, prefixo="", lado="raiz", linhas=None):
    if no == arvore.NIL:
        return linhas
    cor = "V" if no.cor == RED else "N"
    horario, id_paciente = no.chave
    ramo = {"raiz": "", "dir": "┌── ", "esq": "└── "}[lado]
    continua_dir = prefixo + ("    " if lado in ("raiz", "dir") else "│   ")
    continua_esq = prefixo + ("    " if lado in ("raiz", "esq") else "│   ")
    desenhar_arvore(arvore, no.dir, continua_dir, "dir", linhas)
    linhas.append(f"  {prefixo}{ramo}{id_paciente} ({cor}) {horario}")
    desenhar_arvore(arvore, no.esq, continua_esq, "esq", linhas)
    return linhas


def estruturas(sistema):
    print("\n  Árvore Rubro-Negra (V = vermelho, N = negro; direita em cima):")
    linhas = desenhar_arvore(sistema.arvore, sistema.arvore.raiz, linhas=[])
    print("\n".join(linhas) if linhas else "  (vazia)")

    print("\n  Heap de pacientes (raiz = próxima senha):")
    exibir_niveis(sistema.heap.v, lambda paciente: senha(paciente.id, paciente.prioridade))

    print("\n  Heap de médicos disponíveis (concluídos, ordem da última atribuição, ID):")
    exibir_niveis(sistema.heap_medicos.v, lambda medico: f"#{medico.id} {medico.nome} {medico.chave()}")

    print("\n  Tabela Hash da fila de espera:")
    for linha in sistema.espera.exibir().split("\n"):
        print("  " + linha)
    return "Estruturas exibidas."


def exibir_niveis(elementos, formatar):
    if not elementos:
        print("  (vazio)")
        return
    inicio, nivel = 0, 0
    while inicio < len(elementos):
        fim = min(len(elementos), inicio + 2 ** nivel)
        valores = "  ".join(formatar(elemento) for elemento in elementos[inicio:fim])
        print(f"  nível {nivel}: {valores}")
        inicio, nivel = fim, nivel + 1


def cadastrar_equipe_exemplo(sistema):
    for letra in "ABC":
        sistema.cadastrar_medico(f"Médico {letra}", f"FICT-{letra}")


def carregar(sistema):
    print("  1 · Cenário padrão (5 pacientes)")
    print("  2 · Teste de colisões (IDs no mesmo bucket)")
    print("  3 · Começar vazio")
    opcao = ler_inteiro("Cenário", 1, 3)
    if opcao == 1:
        sistema.carregar(SIGAE.CENARIO_PADRAO)
        cadastrar_equipe_exemplo(sistema)
        return "Cenário restaurado: cinco pacientes aguardando, médicos livres."
    if opcao == 2:
        sistema.carregar(SIGAE.CENARIO_COLISAO)
        cadastrar_equipe_exemplo(sistema)
        return "Cenário de colisões: IDs 1000, 1011, 1022, 1033 e 1044 caem no mesmo bucket."
    sistema.limpar()
    cadastrar_equipe_exemplo(sistema)
    return "Fila vazia e equipe de exemplo disponível."


OPERACOES = {
    1: registrar, 2: consultar, 3: reclassificar, 4: cancelar, 5: listar, 6: chamar,
    7: concluir, 8: historico, 9: validar, 10: estruturas, 11: carregar,
    12: cadastrar_medico, 13: consultar_medico,
}


def main():
    sistema = SIGAE()
    sistema.carregar(SIGAE.CENARIO_PADRAO)
    cadastrar_equipe_exemplo(sistema)
    mensagem = "Cenário inicial carregado: cinco pacientes aguardando."

    while True:
        print()
        painel(sistema)
        print(f"  Último registro: {mensagem}")
        print(MENU)
        opcao = ler_inteiro("Opção", 0, max(OPERACOES))
        if opcao == 0:
            print("Até logo.")
            break
        try:
            mensagem = OPERACOES[opcao](sistema)
            sistema.validar()
        except ErroIntegridade as erro:
            mensagem = f"FALHA CRÍTICA: {erro}"
        except ErroSIGAE as erro:
            mensagem = f"ERRO: {erro}"
        except AssertionError as erro:
            mensagem = f"INCONSISTÊNCIA DETECTADA: {erro}"
        print(f"\n  → {mensagem}")
        input("  Enter para continuar...")


def executar():
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nAté logo.")
