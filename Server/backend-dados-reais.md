# Analog Finder: como foi decidido o backend (dados reais)

**Projeto:** NASA Space Apps Challenge 2026, desafio *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*
**Data:** 2026-11-15
**Complementa:** `plano-analog-finder.md` e `mvp-frontend-status.md`

Este documento registra como o time chegou ao desenho do backend e como ele vai trocar os dados mockados do MVP por **dados reais da NASA e de agências parceiras**.

---

## 1. Ponto de partida

O MVP de frontend (React + Vite + TypeScript, globo 3D com `react-globe.gl`) já funciona de ponta a ponta com dados fictícios marcados `_mock: true`:

- `src/data/targets.json`: os 6 alvos na Lua e em Marte;
- grade da Terra gerada no navegador a 1°, a partir da cor do Blue Marble, da latitude e de ruído;
- `src/data/sigmas.json`: tolerâncias e pesos provisórios;
- `src/data/curated.json`: pontos curados com textos escritos e números mock.

A interface, a métrica e os fluxos estão validados. O que falta é **substituir os números inventados por medições reais**, e esse é o papel do backend.

---

## 2. A decisão principal: backend como pipeline offline, sem servidor

### Opções avaliadas

| Opção | Como seria | Por que foi descartada ou escolhida |
|---|---|---|
| A. API própria em tempo real | Servidor que consulta as APIs da NASA a cada clique | **Descartada.** Os dados exigem login (Earthdata), os arquivos são grandes (granules de centenas de MB), a latência seria alta e um servidor pode cair na hora da apresentação. |
| B. Servidor com banco de dados pré-carregado | Backend (ex.: FastAPI + PostGIS) servindo a grade | **Descartada.** Resolve a latência, mas exige hospedagem paga ou instável e mais tempo de DevOps do que os 3 dias permitem. |
| C. Pipeline offline + arquivos estáticos | Script Python roda uma vez, gera JSON, e o site lê esses arquivos | **Escolhida.** Usa dados reais, não tem custo, não depende de servidor e funciona no GitHub Pages. |

### Por que a opção C

1. **Os dados não mudam durante a demo.** Relevo, clima médio, albedo e gelo são propriedades estáveis. Não há ganho em consultar ao vivo.
2. **O valor do projeto está na métrica e na explicação**, não na infraestrutura. Cada hora gasta em servidor é uma hora a menos no painel de comparação.
3. **Robustez na apresentação.** Arquivo estático no GitHub Pages não cai, não expira token e não depende do Earthdata estar no ar.
4. **O cálculo da similaridade já roda no navegador.** O frontend só precisa dos valores de cada célula; a fórmula, os σ e os pesos ficam no cliente e podem ser ajustados sem reprocessar nada.

Em resumo: **"dinâmico para o usuário, pré-calculado por baixo"**. O usuário clica em qualquer ponto da Terra e recebe a comparação na hora, mas os números por trás foram medidos por satélite e processados antes.

---

## 3. Arquitetura

```
┌───────────────────────────── PIPELINE (Python, roda 1x) ─────────────────────────────┐
│                                                                                      │
│  1. Download        earthaccess (Earthdata) / Copernicus Data Space / PDS            │
│  2. Pré-processo    recorte, reprojeção para lat/lon (EPSG:4326), máscara de terra    │
│  3. Derivação       declividade, rugosidade, amplitude térmica, médias anuais         │
│  4. Agregação       reamostragem para a grade de 0,25°                                │
│  5. Alvos           extração dos mesmos parâmetros nos 6 alvos (Lua e Marte)          │
│  6. Validação       checagens de faixa, comparação com valores da literatura         │
│  7. Exportação      earth_grid.json + targets.json + metadata.json                    │
│                                                                                      │
└──────────────────────────────────────────┬───────────────────────────────────────────┘
                                           │ arquivos estáticos em public/data/
                                           ▼
┌──────────────────────────── FRONTEND (já existe) ────────────────────────────────────┐
│  Lê public/data/earth_grid.json; se não existir, usa o mock                          │
│  Clique → busca a célula → calcula a similaridade com sigmas.json → painel           │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**Stack do pipeline:** Python 3.11+, `earthaccess`, `xarray`, `rioxarray`, `rasterio`, `numpy`, `scipy` (filtros de janela) e `pandas`/`pyarrow` para tabelas intermediárias.

**Organização sugerida do repositório:**

```
pipeline/
  00_auth.py            # login Earthdata (credenciais via .netrc, nunca no git)
  10_download_earth.py
  20_download_moon_mars.py
  30_process_relief.py
  31_process_thermal.py
  32_process_surface.py # albedo, NDVI
  33_process_water.py   # chuva, gelo
  40_build_grid.py      # junta tudo na grade de 0,25°
  50_build_targets.py
  60_validate.py
  70_export.py
  config.yaml           # resolução, período, caminhos
data/raw/               # ignorado no git
data/interim/           # ignorado no git
```

---

## 4. Dados reais por parâmetro

Cada parâmetro precisa existir nos três corpos ou ter uma regra clara quando não existe (regra 1 do plano). A escala horizontal de referência é **~2 km** nos três corpos (regra 2).

| # | Parâmetro | Terra (fonte real) | Lua | Marte | Processamento |
|---|---|---|---|---|---|
| 1 | Declividade média (°) | Copernicus DEM GLO-90 (plano B: NASADEM; plano C: ETOPO) | LOLA | MOLA | DEM reamostrado para ~2 km, gradiente, média por célula de 0,25° |
| 2 | Rugosidade (m) | idem | LOLA | MOLA | desvio-padrão da elevação em janela de ~2 km, média por célula |
| 3 | Amplitude térmica dia–noite (K) | MODIS LST mensal **MOD11C3** (dia − noite) | Diviner | Mars Climate Database | média anual da diferença dia − noite |
| 4 | Temperatura mínima (K) | MOD11C3 (noite) | Diviner | Mars Climate Database | mínimo das médias mensais noturnas |
| 5 | Chuva anual (mm), unilateral | GPM IMERG (mensal) | = 0 | = 0 | soma anual, média de vários anos |
| 6 | NDVI, unilateral | MODIS **MOD13C2** | = 0 | = 0 | média anual |
| 7 | Albedo | MODIS **MCD43C3** | albedo LOLA | albedo TES | média anual, white-sky |
| 8 | Iluminação | calculada pela latitude (sem download) | LOLA (iluminação do polo sul) | só para alvos lunares | categórica, derivada no frontend |
| 9 | Gelo no subsolo / permafrost | mapa de permafrost ou cobertura de neve MODIS | gelo em crateras sombreadas (Diviner/LEND) | mapeamento de gelo raso | categórico 0/1 |

**Fora da nota, mas sempre exibidos:** gravidade, pressão atmosférica, radiação e composição do ar. São valores fixos por corpo, de referência, e não precisam de pipeline.

### Regras de processamento comuns

- **Período:** médias de vários anos recentes para os produtos climáticos (o número exato de anos fica em `config.yaml`), para evitar que um ano atípico distorça a célula.
- **Máscara de terra:** só entram células com terra. Oceano não é exportado.
- **Valores faltantes:** a célula recebe `null` no campo e o frontend trata como **N/A**, nunca como zero (mesma regra da métrica).
- **Unidades:** tudo em SI ou unidade declarada no `metadata.json` (K, mm/ano, graus, metros, adimensional).

---

## 5. Os 6 alvos com dados reais

| Alvo | Corpo | Fonte principal |
|---|---|---|
| Shackleton / *connecting ridge* | Lua | LOLA (relevo, iluminação), Diviner (temperatura) |
| Cratera permanentemente sombreada (Cabeus) | Lua | LOLA, Diviner, LEND (hidrogênio/gelo) |
| Mare Tranquillitatis | Lua | LOLA, Diviner |
| Cratera Jezero | Marte | MOLA, TES, Mars Climate Database |
| Cratera Gale | Marte | MOLA, TES, Mars Climate Database |
| Arcadia Planitia | Marte | MOLA, TES, MCD, mapeamento de gelo raso |

Para cada alvo, o pipeline extrai os parâmetros em uma janela ao redor do ponto central e registra a **fonte e o produto exato** de cada valor no próprio `targets.json`, para que o painel possa citar de onde veio cada número.

Como são só 6 pontos, parte desses valores pode ser obtida diretamente de mapas e tabelas publicados das missões, desde que a fonte fique registrada. Isso reduz o risco de baixar mosaicos globais pesados de Lua e Marte para usar só 6 pixels.

---

## 6. Contrato com o frontend

O contrato já foi fixado no MVP e o backend precisa respeitá-lo:

### `public/data/earth_grid.json`

```json
{
  "_mock": false,
  "res_deg": 0.25,
  "generated_at": "2026-11-15",
  "fields": ["slope_deg","roughness_m","temp_range_k","temp_min_k","precip_mm","ndvi","albedo","ground_ice"],
  "cells": [[lat, lon, ...valores na ordem de fields]]
}
```

- Só células de terra; `lat`/`lon` no **centro** da célula.
- `ground_ice` é 0 ou 1.
- Iluminação **não** vai no arquivo: o frontend deriva da latitude.
- Valores arredondados (ex.: 1 casa decimal para temperaturas, 2 para NDVI e albedo) para reduzir o tamanho.

### `public/data/targets.json`

Mesmo formato do mock atual, com `"_mock": false` e um bloco `sources` por alvo:

```json
{
  "id": "moon_shackleton_ridge",
  "body": "moon",
  "params": { "slope_deg": 0, "roughness_m": 0, "...": "valores reais" },
  "sources": { "slope_deg": "LOLA ...", "temp_min_k": "Diviner ..." },
  "_mock": false
}
```

### `public/data/metadata.json` (novo)

Lista, para cada campo, a fonte, o produto, o período, a unidade e a versão do pipeline. Serve para o painel de créditos e para responder aos jurados de onde vem cada número.

### Tamanho do arquivo

Uma grade global de 0,25° só com terra tem na ordem de **300 mil células**. Com 10 valores por célula, o JSON fica com dezenas de MB antes da compressão. Opções, em ordem de preferência:

1. JSON compacto com valores arredondados (o GitHub Pages serve com gzip);
2. dividir em blocos de 10° × 10° carregados sob demanda;
3. formato binário (`earth_grid.bin` com `Float32Array`) se as duas primeiras não bastarem.

---

## 7. Validação dos dados reais

Antes de remover o mock, o pipeline roda `60_validate.py`:

- **Faixas físicas:** temperaturas entre ~180 K e ~340 K na Terra, NDVI entre −1 e 1, albedo entre 0 e 1, declividade entre 0° e 90°.
- **Cobertura:** percentual de células com cada campo preenchido; campos com muitos `null` são sinalizados.
- **Pontos de controle:** os pontos curados (Atacama, McMurdo, Haughton, Askja, Mauna Loa, Araguainha) precisam ter valores coerentes com o que se sabe deles. Por exemplo, Atacama com chuva quase nula e McMurdo com temperaturas mínimas muito baixas e gelo.
- **Sanidade da métrica:** com os dados reais, os análogos clássicos (Atacama para Marte, Antártida para a Lua polar) devem aparecer bem colocados no ranking. Se não aparecerem, o problema está nos σ ou no dado, e isso é investigado antes da apresentação.

---

## 8. Transição do mock para o real

1. O pipeline grava os arquivos em `public/data/`.
2. O frontend, ao encontrar `earth_grid.json` com `"_mock": false`, ignora a grade gerada no navegador.
3. `src/data/targets.json` mockado é substituído pelo real.
4. Os números de `curated.json` passam a ser lidos da grade real (os textos continuam escritos à mão).
5. O selo de "dados de demonstração" na interface some quando nenhum arquivo ativo tem `_mock: true`.

---

## 9. Riscos e planos B

| Risco | Plano B |
|---|---|
| Download do Copernicus DEM global é pesado demais | NASADEM ou ETOPO, já mais grossos; ou processar só os continentes em blocos |
| Login Earthdata atrasa | Criar a conta no primeiro momento (urs.earthdata.nasa.gov); algumas camadas podem vir de versões já agregadas |
| Mars Climate Database não tem download simples | Usar valores publicados para os 3 alvos de Marte, com fonte citada |
| Grade não termina a tempo | Exportar só as regiões dos pontos curados em 0,25° e manter o restante do globo em 1° |
| Arquivo final grande demais | Blocos de 10° ou binário (seção 6) |

---

## 10. O que continua em aberto

1. Escolha final do mapa de permafrost para a Terra.
2. Período exato (anos) das médias climáticas.
3. Formato final da grade (JSON único, blocos ou binário), decidido após medir o tamanho real.
4. Justificativa de cada σ em uma frase, agora com base na distribuição dos dados reais.
5. Pesos de cada dimensão.

---

## Resumo para o pitch

> "Não temos servidor. Baixamos dados reais de satélite da NASA e da ESA (relevo, temperatura, chuva, vegetação, albedo e gelo), processamos uma vez em Python para uma grade global de 0,25° e entregamos tudo como arquivos estáticos. Na Lua e em Marte usamos LOLA, Diviner, LEND, MOLA e TES. O navegador calcula a similaridade na hora, e cada número no painel diz de qual instrumento veio."
