# Shadow Fansub — Projetos

Repositório destinado à organização dos projetos da **Shadow Fansub**.  


## Projetos

### Ultraman

-  **Ultraman Nexus**

## Configuração do Git

Para garantir a padronização das legendas e evitar commits com inconsistências, o projeto inclui **ganchos Git** (`.githooks`).

### Ativando o *pre-commit hook* local

1. Clone o repositório normalmente:
   ```bash
   git clone https://github.com/shadowfansub/project.git
   cd project
   ```

2. Configure o Git para usar o diretório de hooks local:
   ```bash
   git config core.hooksPath .githooks
   ```

O *hook* `pre-commit` executará automaticamente verificações básicas antes de cada commit.
