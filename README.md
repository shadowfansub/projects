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

## Mux Automatizado

Para realizar o mux automatizado dos episódios, utilize o script `mux.py` localizado na raiz do repositório.

```bash
python mux.py caminho/para/o/projeto
```

Se o projeto estiver devidamente configurado com o arquivo de configuração `config.toml`, o script realizará o mux automaticamente. Caso o projeto não tenha um arquivo de configuração, use o template abaixo:

```toml
show_name = "Nome da Série"
fansub_group = "Nome do Grupo"
video_source = "Fonte do Vídeo"
audio_language = "Idioma do Áudio"
audio_lang_code = "código"
sub_language = "Idioma da Legenda"
sub_lang_code = "código"
tmdb_id = 0
ycbcr_matrix = "TV.709"
resolution = [1920, 1080]

translation = "Nome do Tradutor"
editing = "Nome do Editor"
translation_checking = "Nome do Revisor"
timing = "Nome do Timer"
typesetting = "Nome do Typesetter"
quality_checking = "Nome do QC"

episodes_path = "./episodes"
extras_path = "./common/songs"
output_path = "./muxed"

episodes = "1...10"

[extras.merge."1-5"]
"opening_01.ass" = { from = "opsync", to = "sync" }
"ending_01.ass" = { from = "edsync", to = "sync" }

[extras.merge."6-10"]
"opening_02.ass" = { from = "opsync", to = "sync" }
"ending_02.ass" = { from = "edsync", to = "sync" }
```