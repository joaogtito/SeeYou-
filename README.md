
<p align="center">
  <img src="https://raw.githubusercontent.com/joaogtito/SeeYou-/refs/heads/feat/readme-update/github_logo.png" alt="Logo da SeeYou Finder"/>
</p>

O **SeeYou Finder** é uma ferramenta de analise de dados avançada com um visualizador em globo 3D com três corpos (Terra, Lua, Marte).

Na Terra, clique em qualquer ponto para comparar a célula da grade com um dos 6 alvos. O painel mostra a nota por dimensão, mostra a justificativa da nota e explicita o que a Terra nunca reproduz.

> **Os números desta versão são fictícios.** A grade da Terra é estimada pela cor do mosaico Blue Marble, pela latitude e por ruído. Os valores dos alvos, as tolerâncias σ e os pesos são provisórios. Só as imagens de satélite são reais.

## Nosso Desafio

**Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars**

## Como Rodar Localmente

```bash
git clone https://github.com/joaogtito/SeeYou-.git 

cd SeeYou-

npm install
npm run dev
```

Após executar estes comandos a ferramenta poderá ser aberta em `http://localhost:5173`

## Funcionalidades da Ferramenta

- Troca Terra / Marte / Lua com o tema de cada corpo (azul, laranja, cinza) do Figma.
- Clique direto em qualquer ponto da Terra: destaca a célula e abre a comparação.
- Métrica do plano rodando no navegador (`src/lib/metric.ts`), com N/A para dimensão que não se aplica.
- Top Locais, mostra os melhores análogos do alvo ativo, com separação mínima entre eles.
- Camadas SAT, FOLHAGEM (NDVI), CALOR (LST) e SIMILARIDADE (mapa de calor da nota).
- 6 pontos curados com texto, incluindo Araguainha marcada como "Descoberta".
- Vista de Lua e Marte com os 3 alvos de cada corpo e o botão "Ver análogos na Terra".
- Busca, português/inglês, escala, altitude e coordenadas.

## Fontes das imagens

- **Terra:** NASA GIBS (Blue Marble, MODIS NDVI 8 dias, MODIS LST dia), WMTS EPSG:4326.
- **Lua:** NASA Moon Trek, mosaico LRO WAC.
- **Marte:** NASA Mars Trek, mosaico Viking MDIM 2.1.

