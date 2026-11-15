# SeeYou

## Estrutura

- `Client/` — front-end (React + Vite + TypeScript). Comandos npm rodam dentro desta pasta.
- `Server/` — back-end (Python, gerenciado com `uv`). Comandos rodam dentro desta pasta com `uv run ...`.

## Regras

### Git
- **Nunca** execute nenhum comando git (incluindo `status`, `diff`, `log`, `add`, `commit`, `push`, `checkout`, `mv` etc.) sem pedir permissão explícita ao usuário antes.

### Graphify
- **Sempre** rode o graphify depois de mudanças grandes de código (novos módulos, refatorações, mudanças que afetam vários arquivos).
- Rode também se já faz muito tempo desde a última execução (ex.: várias tarefas seguidas sem rodar).
- O graphify está instalado como dependência de dev em `Server/`. Para atualizar o grafo do projeto inteiro, rode da raiz do repositório:
  ```bash
  uv run --project Server graphify update .
  ```
  A saída fica em `graphify-out/` (ignorada pelo git). Consulte o grafo com `graphify query`, `explain`, `path` e `god-nodes`.
