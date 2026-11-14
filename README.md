# Analog Finder (MVP com dados mockados)

Projeto do NASA Space Apps: *Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars*.

Globo 3D com três corpos (Terra, Lua, Marte). Na Terra, clique em qualquer ponto para comparar a célula da grade com um dos 6 alvos. O painel mostra a nota por dimensão, o **Por quê?**, o **Por que não?** e o que a Terra nunca reproduz.

> **Os números desta versão são fictícios.** A grade da Terra é estimada pela cor do mosaico Blue Marble, pela latitude e por ruído. Os valores dos alvos, as tolerâncias σ e os pesos são provisórios. Só as imagens de satélite são reais.

## Rodar

```bash
npm install
npm run dev        # abre em http://localhost:5173
npm run build      # gera dist/ (estático, pronto para o GitHub Pages)
npm run check      # testa a métrica no Node (22.18+ ou 24), sem navegador
```

## O que já funciona

- Troca Terra / Marte / Lua com o tema de cada corpo (azul, laranja, cinza) do Figma.
- Clique direto em qualquer ponto da Terra: destaca a célula e abre a comparação.
- Métrica do plano rodando no navegador (`src/lib/metric.ts`), com N/A para dimensão que não se aplica.
- **Top Locais**: melhores análogos do alvo ativo, com separação mínima entre eles.
- Camadas SAT, FOLHAGEM (NDVI), CALOR (LST) e SIMILARIDADE (mapa de calor da nota).
- 6 pontos curados com texto, incluindo Araguainha marcada como "Descoberta".
- Vista de Lua e Marte com os 3 alvos de cada corpo e o botão "Ver análogos na Terra".
- Busca, português/inglês, escala, altitude e coordenadas.

## Estrutura

```
src/
  App.tsx                 estado e layout
  components/
    GlobeView.tsx         globo 3D (react-globe.gl)
    Panels.tsx            barra superior, Top Locais, painéis de comparação, barra inferior
    Icons.tsx             ícones e logo em SVG
  lib/
    metric.ts             métrica de similaridade e ranking
    mockGrid.ts           gerador da grade mockada + leitor do arquivo real
    textures.ts           monta as texturas a partir dos tiles da NASA
    types.ts              formato dos dados
  data/
    targets.json          6 alvos (MOCK)
    sigmas.json           tolerâncias, tabelas categóricas e pesos (PROVISÓRIO)
    curated.json          pontos curados e textos
    gazetteer.json        nomes de regiões para a busca e para o Top Locais
  i18n.ts                 textos PT/EN
public/data/
  earth_grid.sample.json  exemplo do formato da grade real
```

## Trocar o mock pelos dados do pipeline

1. **Grade da Terra.** Gere `public/data/earth_grid.json` no formato abaixo. Se o arquivo existir, o app usa ele e ignora o gerador mock; o selo "Dados fictícios" some quando `_mock` é `false`.

   ```json
   {
     "_mock": false,
     "res_deg": 0.25,
     "fields": ["slope_deg", "roughness_m", "temp_range_k", "temp_min_k", "precip_mm", "ndvi", "albedo", "ground_ice"],
     "cells": [[lat, lon, 3.0, 40, 20.0, 285.0, 1500, 0.5, 0.15, 0]]
   }
   ```

   Só células de terra, `lat`/`lon` no centro da célula, `ground_ice` como 0 ou 1. O regime de iluminação é calculado pela latitude.
   A 0,25° são cerca de 300 mil células: em JSON fica pesado (dezenas de MB). Para a demo, 0,5° ou um binário resolvem.

2. **Alvos.** Substitua os valores de `params` em `src/data/targets.json` pelos perfis de LOLA, Diviner, MOLA e MCD e remova `"_mock": true`.

3. **Tolerâncias e pesos.** Ajuste `src/data/sigmas.json` e escreva a justificativa de cada σ.

## Fontes das imagens

- Terra: NASA GIBS (Blue Marble, MODIS NDVI 8 dias, MODIS LST dia), WMTS EPSG:4326.
- Lua: NASA Moon Trek, mosaico LRO WAC.
- Marte: NASA Mars Trek, mosaico Viking MDIM 2.1.

Os tiles são colados em um canvas equirretangular no navegador e viram a textura do globo. Se a rede falhar, o app usa uma textura de reserva.

## Diferenças em relação ao Figma

- O logo é o SeeYou! Finder (`src/assets/logo-seeyou.png`). Os ícones foram redesenhados em SVG (`Icons.tsx`) e os botões de planeta são feitos em CSS, porque os assets do Figma não puderam ser baixados. Para usar os originais, exporte-os e troque nesses pontos.
- As miniaturas dos cards são gradientes pela classe do terreno, sem fotos.
- Sem o logo da NASA.
