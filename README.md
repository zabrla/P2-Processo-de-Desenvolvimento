# SIGAE

Trabalho final de Estrutura de Dados Avançados (Universidade de Vassouras).

O SIGAE é um sistema de terminal, em Python, que organiza a fila de um pronto-atendimento. Tem dois médicos atendendo ao mesmo tempo e os pacientes são chamados por urgência, não por ordem de chegada.

O sistema precisa responder três perguntas o tempo todo, e cada uma é respondida por uma estrutura feita pelo grupo:

| Pergunta | Estrutura | Arquivo |
|---|---|---|
| Quem é o próximo a ser atendido? | Min-Heap | `sigae/estruturas/heap.py` |
| Em que ordem os pacientes chegaram? | Árvore Rubro-Negra | `sigae/estruturas/arvore_rubro_negra.py` |
| Onde está o paciente com este ID? | Tabela Hash | `sigae/estruturas/tabela_hash.py` |

Nenhuma delas usa `dict`, `heapq` ou biblioteca pronta de árvore para guardar os pacientes.

## Como rodar

Precisa só do Python 3, sem instalar nada. Na pasta do projeto:

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
main.py                          ponto de entrada (é o que você executa)
sigae/
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
