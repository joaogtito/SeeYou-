# SeeYou: pipeline de dados reais

O backend do SeeYou é um **pipeline offline** em Python, sem servidor. Ele roda uma vez, baixa dados reais de satélite (NASA, ESA, USGS) e grava arquivos estáticos que o frontend lê:

| Arquivo | Conteúdo |
|---|---|
| `Client/public/data/earth_grid.json` | grade da Terra de 0,25°, só células de terra, 8 parâmetros por célula |
| `Client/public/data/metadata.json` | fonte, produto, período e unidade de cada campo |
| `Client/src/data/targets.json` | os 6 alvos (Lua/Marte) com valores reais e o bloco `sources` |

## Instalação

```bash
cd Server
uv sync            # Python 3.12 (fixado em .python-version)
uv run pytest      # testes com dados sintéticos, sem rede
```

## Login no Earthdata (uma vez)

Crie uma conta em <https://urs.earthdata.nasa.gov> e rode:

```bash
uv run python pipeline/00_auth.py --interactive
```

As credenciais são gravadas em `~/.netrc` (no Windows, `%USERPROFILE%\_netrc`), **fora do repositório**. Para alguns produtos, a primeira vez exige aprovar a aplicação "LP DAAC Data Pool" / "NASA GESDISC DATA ARCHIVE" no seu perfil do Earthdata.

## Rodando

```bash
uv run python pipeline/run_all.py                 # tudo, de 00 a 70
uv run python pipeline/run_all.py --from 30       # só o processamento
uv run python pipeline/10_download_earth.py --only lst,ndvi   # parte dos downloads
```

| Script | O que faz | Precisa de login? |
|---|---|---|
| `00_auth.py` | login Earthdata | sim |
| `10_download_earth.py` | MOD11C3, MOD13C2, MCD43C3 (1 dia/mês), GPM IMERG, MOD10CM, CCI Permafrost | sim (menos o CCI) |
| `20_download_moon_mars.py` | recortes LOLA/MOLA em volta dos 6 alvos (leitura parcial via HTTP, alguns MB) | não |
| `30_process_relief.py` | declividade e rugosidade a ~2 km (Copernicus GLO-90 via S3 público) + máscara de terra | não |
| `31_process_thermal.py` | amplitude dia − noite e mínima (MOD11C3) | – |
| `32_process_surface.py` | NDVI (MOD13C2) e albedo white-sky (MCD43C3) | – |
| `33_process_water.py` | chuva anual (IMERG) e gelo (CCI Permafrost ≥ 50% ou neve permanente MOD10CM) | – |
| `40_build_grid.py` | junta tudo na grade de 0,25° | – |
| `50_build_targets.py` | alvos: relevo calculado do DEM + valores publicados de `targets_published.yaml` | – |
| `60_validate.py` | faixas físicas (**bloqueia**), cobertura, pontos de controle, sanidade da métrica (avisos) | – |
| `70_export.py` | grava os JSON do frontend (recusa se a validação falhou) | – |

Tudo se configura em [`pipeline/config.yaml`](pipeline/config.yaml): período (2015–2024), fonte do relevo (`glo90` ou `etopo`), limiares, faixas de validação etc. Dados brutos vão para `data/raw/` e intermediários para `data/interim/` (ambos fora do git). O relatório de validação fica em `data/interim/validation_report.md`.

### Custo e tempo aproximados

- **Relevo GLO-90:** ~26 mil tiles lidos direto do S3, sem guardar nada (~2 s por tile; com 8 processos, ~2 h). Para um teste rápido, use `--max-tiles 50`. Se não der, troque para `relief.source: etopo` (288 tiles do ETOPO 2022 15", baixados antes pelo `10_download_earth.py`).
- **Clima:** cerca de 120 arquivos mensais por produto (10 anos).
- **Lua/Marte:** só os 6 recortes, sem baixar os mosaicos globais.

## Organização do código

- `pipeline/`: scripts finos e numerados, `config.yaml` e `targets_published.yaml` (valores da Lua e de Marte, com fonte e grau de confiança).
- `src/seeyou_server/`: funções puras e testáveis (`grid`, `relief`, `climate`, `readers`, `dem_earth`, `planetary`, `targets`, `metric`, `validate`, `export`, `download`).
- `tests/`: pytest com dados sintéticos.

`metric.py` é uma cópia da métrica de `Client/src/lib/metric.ts`, usada na checagem de sanidade. Se a fórmula mudar no frontend, mude aqui também.
