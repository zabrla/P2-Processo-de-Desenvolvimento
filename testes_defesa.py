from sigae.interface import desenhar_arvore, exibir_niveis
from sigae.sistema import SIGAE, ErroSIGAE, senha


def imprimir_detalhes_estruturas(sistema):
    print("  [DETALHES DAS ESTRUTURAS]")
    linhas_rb = desenhar_arvore(sistema.arvore, sistema.arvore.raiz, linhas=[])
    print("  1. Árvore Rubro-Negra (Percurso em-ordem):")
    print("\n".join("   " + l for l in linhas_rb) if linhas_rb else "     (vazia)")
    chegadas = [f"{f.horario}(ID:{f.id})" for f in sistema.lista_por_chegada()]
    print(f"     -> Sequência cronológica: {chegadas}")

    print("  2. Min-Heap (Raiz = menor chave (prioridade, chegada, ID)):")
    exibir_niveis(
        sistema.heap.v,
        lambda p: f"{senha(p.id, p.prioridade)}[P{p.prioridade}, {int(p.chegada)}min]",
    )

    print("  3. Tabela Hash (Buckets e colisões):")
    for linha in sistema.espera.exibir().split("\n"):
        print("     " + linha)

    print("  4. Fonte única de dados (endereços de memória):")
    for id_pac in sorted(sistema.espera.chaves()):
        ficha = sistema.localizar(id_pac)
        obj_hash = sistema.espera.buscar(id_pac)
        obj_rb = sistema.arvore.buscar(ficha.horario, id_pac).dado
        obj_heap = sistema.heap.buscar(id_pac)
        print(
            f"     -> ID {id_pac}: Hash={hex(id(obj_hash))} | "
            f"RB={hex(id(obj_rb))} | Heap={hex(id(obj_heap))}"
        )


def verificar_cenario(nome_teste, sistema, condicao_ok, motivo_sucesso, motivo_erro, mostrar_detalhes=True):
    print("=" * 74)
    print(f"TESTE: {nome_teste}")
    print("-" * 74)

    try:
        sistema.validar()
        integridade_ok = True
        erro_integridade = ""
    except Exception as erro:
        integridade_ok = False
        erro_integridade = str(erro)

    if not integridade_ok:
        print("STATUS: [FALHOU / NÃO FUNCIONANDO]")
        print(f"RAZÃO: Violação de integridade interna das estruturas -> {erro_integridade}")
        print("=" * 74 + "\n")
        return False

    if condicao_ok:
        print("STATUS: [PASSOU / FUNCIONANDO CORRETAMENTE]")
        print(f"POR QUE ESTÁ CERTO: {motivo_sucesso}")
        if mostrar_detalhes:
            print()
            imprimir_detalhes_estruturas(sistema)
    else:
        print("STATUS: [FALHOU / NÃO FUNCIONANDO]")
        print(f"RAZÃO DO ERRO: {motivo_erro}")
        if mostrar_detalhes:
            print()
            imprimir_detalhes_estruturas(sistema)

    print("=" * 74 + "\n")
    return condicao_ok


def testar_entrada_invalida(nome_teste, sistema, funcao_acao, descricao_entrada):
    print("=" * 74)
    print(f"TESTE DE BLOQUEIO: {nome_teste}")
    print("-" * 74)
    try:
        funcao_acao()
        print("STATUS: [FALHOU / NÃO FUNCIONANDO]")
        print(
            f"RAZÃO DO ERRO: O sistema ACEITOU '{descricao_entrada}', mas deveria ter bloqueado "
            f"por violar as regras de negócio ou formatação."
        )
    except (ErroSIGAE, ValueError, KeyError, TypeError) as erro_capturado:
        sistema.validar()
        print("STATUS: [PASSOU / FUNCIONANDO CORRETAMENTE]")
        print(
            f"POR QUE ESTÁ CERTO: O sistema recusou '{descricao_entrada}' como esperado "
            f"e manteve os 3 índices intactos (rollback). Mensagem: '{erro_capturado}'"
        )
    print("=" * 74 + "\n")


if __name__ == "__main__":
    # =========================================================================
    # ÁREA DE TESTE ALTERARANDO VALORES (CERTOS E ERRADOS)
    # =========================================================================

    # 1: TESTE DE EMPATES
    s1 = SIGAE()
    s1.cadastrar("Carlos", "08:30", 2, id_paciente=105)
    s1.cadastrar("Ana", "08:30", 2, id_paciente=100)
    s1.cadastrar("Beatriz", "08:15", 2, id_paciente=110)

    proximo = s1.proximo_da_fila()
    id_esperado_na_raiz = 110  # <-- MUDAR VALOR PARA VER O PRINT DE ERRO Ex: 105

    verificar_cenario(
        nome_teste="Desempate no Min-Heap (Mesma prioridade 2, horários 08:15 vs 08:30)",
        sistema=s1,
        condicao_ok=(proximo is not None and proximo.id == id_esperado_na_raiz),
        motivo_sucesso=(
            f"Todos têm prioridade 2, mas o ID {proximo.id} ({proximo.nome}) chegou às {proximo.horario} "
            f"(mais cedo que 08:30), assumindo corretamente a raiz do Min-Heap."
        ),
        motivo_erro=(
            f"Era esperado o ID {id_esperado_na_raiz} como próximo da fila, mas a raiz do Heap "
            f"entregou o ID {proximo.id if proximo else 'Nenhum'} ({proximo.nome if proximo else ''})."
        ),
    )

    # 2: TESTE DE COLISÕES NA HASH
    s2 = SIGAE()
    ids_teste = [1000, 1011, 1022]
    for idx, pid in enumerate(ids_teste):
        s2.cadastrar(f"Paciente_{pid}", f"09:0{idx}", 3, id_paciente=pid)

    colisoes_esperadas = 2  # <-- MUDAR O VALOR PARA VER O PRINT DE ERRO Ex: 0 OU 5 
    colisoes_reais = s2.espera.colisoes()

    verificar_cenario(
        nome_teste="Colisões forçadas na Tabela Hash (1000, 1011, 1022 % 11 == 10)",
        sistema=s2,
        condicao_ok=(colisoes_reais == colisoes_esperadas),
        motivo_sucesso=(
            f"Os 3 IDs caíram no mesmo bucket [10], gerando exatamente {colisoes_reais} colisões "
            f"encadeadas e todos continuam localizáveis em O(1) médio."
        ),
        motivo_erro=(
            f"Esperava {colisoes_esperadas} colisões na Tabela Hash, mas foram registradas "
            f"{colisoes_reais} colisões."
        ),
    )

    # 3. TESTE DE VALIDAÇÃO DE ENTRADA (Teste com valor errado vs valor certo)
    s3 = SIGAE()
    horario_para_testar = "9:30"  # <-- MUDAR VALOR PARA VER O TESTE DE BLOQUEIO FALHAR Ex: "09:30"

    testar_entrada_invalida(
        nome_teste="Bloqueio de horário sem zero à esquerda (HH:MM)",
        sistema=s3,
        funcao_acao=lambda: s3.cadastrar("Teste Horário", horario_para_testar, 1, id_paciente=500),
        descricao_entrada=f"horário='{horario_para_testar}'",
    )