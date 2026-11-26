# SIGAE

Trabalho final de Estrutura de Dados Avançados (Universidade de Vassouras).

O SIGAE organiza a fila de um pronto-atendimento demonstrativo em Python. Dois consultórios compartilham a mesma fila, e a chamada considera a classificação de risco, o horário de chegada e o número da ficha. Há uma interface web em Streamlit com SQLite e um menu de terminal para demonstrar as estruturas de dados.

O sistema precisa responder três perguntas o tempo todo, e cada uma é respondida por uma estrutura feita pelo grupo:

| Pergunta | Estrutura | Arquivo |
|---|---|---|
| Quem é o próximo a ser atendido? | Min-Heap | `sigae/estruturas/heap.py` |
| Em que ordem os pacientes chegaram? | Árvore Rubro-Negra | `sigae/estruturas/arvore_rubro_negra.py` |
| Onde está o paciente com este ID? | Tabela Hash | `sigae/estruturas/tabela_hash.py` |

Nenhuma delas usa `dict`, `heapq` ou biblioteca pronta de árvore para guardar os pacientes.

## Como rodar a interface web

Com Python 3.11 ou superior, execute na raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

No Windows PowerShell, crie o ambiente com `py -m venv .venv` e ative-o com `.\.venv\Scripts\Activate.ps1`. Abra o endereço exibido no terminal, geralmente `http://localhost:8501`.

### Fluxo web

- **Visão geral e consultórios** mostram a próxima senha e o estado dos dois consultórios. Use **Chamar** para iniciar e **Concluir atendimento** para liberar o consultório.
- **Novo paciente** registra nome, horário, classificação de 1 a 5 e um número opcional. O número automático começa em 1000 e pula os já utilizados.
- **Fila de espera** mostra a ordem de chamada e permite reclassificar ou cancelar. **Chegadas** exibe a fila na ordem da árvore rubro-negra.
- **Pacientes** consulta pela senha completa. **Histórico** lista atendimentos concluídos ou cancelados, do mais recente ao mais antigo.
- **Estruturas** exibe o heap, a árvore e a hash. Em uma base vazia, também permite carregar dados de exemplo.

A senha `P-<id>` identifica as prioridades 1 a 3. A senha `N-<id>` identifica as prioridades 4 e 5. O painel chama pela senha, com menor prioridade numérica primeiro, seguido de horário de chegada e número da ficha. Se a reclassificação cruza a divisão entre P e N, o prefixo muda e o número permanece.

### Banco de dados

A interface web cria `sigae.db` na raiz na primeira abertura. O arquivo começa vazio e preserva as fichas, as classificações, os consultórios ocupados e o histórico entre reinicializações. Cada interação lê os dados do SQLite para reconstruir os índices do SIGAE. Para consultar mudanças de outra sessão, use **Atualizar dados**. As alterações executam em transações SQLite com SQL escrito diretamente em `sigae/banco.py`.

Para usar outra base, defina `SIGAE_DB_PATH` com o caminho do arquivo SQLite. Exemplo no Linux/macOS:

```bash
SIGAE_DB_PATH=/tmp/sigae-demo.db python -m streamlit run app.py
```

Use dados fictícios nesta aplicação acadêmica.

## Como rodar o menu de terminal

O menu de terminal roda em memória com o Python 3. Na pasta do projeto:

```bash
python main.py
```

O sistema já abre com cinco pacientes de exemplo. Para começar do zero, use a opção 11.

## O que dá para fazer no menu

1. **Registrar entrada**: nome, hora de chegada e classificação de risco, de 1 (emergência) a 5 (não urgente). O número de atendimento é gerado sozinho, mas também dá para digitar um.
2. **Consultar ID**: procura o paciente pela Tabela Hash e mostra a situação dele (aguardando, em atendimento, concluído ou cancelado).
3. **Reclassificar**: muda a prioridade de quem está aguardando. O Heap se reorganiza e o menu mostra quem passou a ser o próximo.
4. **Cancelar**: tira da fila um paciente que ainda não foi chamado.
5. **Lista por chegada**: mostra a fila na ordem em que as pessoas chegaram, usando o percurso em ordem da Rubro-Negra.
6. **Chamar próximo da fila**: o médico livre chama o paciente mais urgente, que é a raiz do Heap. Se os dois médicos estiverem ocupados, o sistema não deixa chamar.
7. **Concluir atendimento**: libera o médico. Se os dois estiverem atendendo, o sistema pergunta qual terminou.
8. **Histórico**: atendimentos concluídos e cancelados.
9. **Validar índices**: confere se as três estruturas estão corretas e com os mesmos pacientes.
10. **Ver estruturas**: desenha a árvore (com as cores dos nós), o heap por nível e os buckets da hash.
11. **Carregar cenário**: o cenário padrão, um cenário de colisões (IDs que caem no mesmo bucket da hash) ou o sistema vazio.

## Como as estruturas ficam sincronizadas

A Hash, a Árvore e o Heap guardam sempre os mesmos pacientes: os que estão **aguardando**. Quando alguém é chamado ou cancelado, sai das três ao mesmo tempo. Quem já saiu da fila continua registrado numa segunda Tabela Hash, a de fichas, e por isso ainda dá para consultar o ID depois.

Toda operação que mexe nas estruturas é "tudo ou nada". Se a inserção ou a remoção falhar no meio, o sistema desfaz o que já tinha feito, para não sobrar paciente em uma estrutura e faltar em outra.

Depois de cada operação do menu, o sistema roda a validação completa:

- a árvore continua respeitando as regras da rubro-negra;
- o heap continua com o menor valor na raiz;
- cada ID da hash está no bucket certo;
- as três estruturas têm exatamente os mesmos IDs.

Se alguma coisa estiver errada, aparece um aviso de inconsistência.

## Detalhes de cada estrutura

**Min-Heap.** Ordena por prioridade, depois por horário de chegada e depois por ID. Assim, entre dois pacientes com a mesma urgência, quem chegou primeiro é chamado primeiro. Inserir, extrair o mínimo e alterar a prioridade custam O(log n).

**Árvore Rubro-Negra.** A chave é o par (horário, ID). Tem inserção e remoção com recoloração e rotações, busca, percurso em ordem e uma função que verifica as propriedades da árvore.

**Tabela Hash.** A função é `ID % capacidade`, e as colisões são tratadas por encadeamento separado: cada bucket é uma lista ligada. A capacidade começa em 11 e é sempre um número primo, o que espalha melhor os IDs. Quando a tabela passa de 75% de ocupação, ela dobra de tamanho e redistribui todos os registros.

## Arquivos

```
app.py                           interface web em Streamlit
main.py                          ponto de entrada do terminal
requirements.txt                 dependência da interface web
sigae/
├── banco.py                     persistência SQLite da interface web
├── interface.py                 menu do terminal
├── sistema.py                   integração das três estruturas e regras do atendimento
├── modelos/
│   └── paciente.py              dados do paciente
└── estruturas/
    ├── heap.py                  Min-Heap
    ├── arvore_rubro_negra.py    Árvore Rubro-Negra
    └── tabela_hash.py           Tabela Hash
```

A pasta `estruturas` tem só as estruturas de dados, sem nenhuma regra do hospital. Quem conhece o atendimento (médicos, fila, histórico) é o `sistema.py`, e o `interface.py` só conversa com o usuário. Dá para trocar o menu por outra interface sem mexer nas estruturas.
