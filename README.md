# Shadow Fansub — Projetos

Repositório destinado à organização dos projetos da **Shadow Fansub**.  


## 📺 Projetos

### Ultraman

-  **Ultraman Nexus**

## 🧰 Ferramentas

### **Fuzzy Text Checker**

Ferramenta interna desenvolvida para auxiliar o processo de revisão textual.  
Ela recebe uma lista de termos de referência (por exemplo, nomes padronizados, termos técnicos, etc.) e analisa um texto de entrada para identificar **divergências**, como:

- Diferenças de grafia (acentos, capitalização, hífens, etc.);
- Termos inconsistentes com o guia de tradução;
- Ocorrências próximas de palavras incorretas via *fuzzy matching*.

Essa ferramenta é especialmente útil para revisar scripts de legendas antes do commit final.


## ⚙️ Configuração do Git

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
