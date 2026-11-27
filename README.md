# Redundância do acesso viário em escala de bairro

Código, dados e figuras do estudo "Redundância do Acesso Viário em Escala de Bairro: Fluxo
Máximo em Nove Bairros do Rio de Janeiro".

O estudo modela as redes viárias do OpenStreetMap como grafos dirigidos e mede o fluxo de
acesso de cada bairro, isto é, o número de rotas disjuntas do núcleo do bairro até as suas
portas de acesso, calculado por fluxo máximo e corte mínimo. Os nove bairros são Urca, Leme,
Alto da Boa Vista, Cosme Velho, Joá, São Conrado, Copacabana, Botafogo e Praça da Bandeira.

## Conteúdo

| Caminho | O que é |
|---|---|
| `grafos/` | Código, dados e saídas. O `grafos/README.md` traz a instalação, o tutorial e o mapa de cada tabela e figura do artigo. |
| `Figures/` | Figuras do artigo, geradas pelo código. |

## Como reproduzir

Requer Python 3.13. Os passos completos, os dados e os tempos de cada etapa estão em
[`grafos/README.md`](grafos/README.md). Em resumo, a partir de `grafos/`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd src
python executar_pipeline.py --listar
```

Os extratos do OpenStreetMap e os polígonos dos bairros já estão em `grafos/data/`, de modo que
a maior parte do pipeline roda sem internet.

## Dados

Dados do mapa © colaboradores do OpenStreetMap (ODbL). Polígonos dos bairros da camada "Limite
de Bairros" do Data.Rio (Instituto Pereira Passos). Censo 2022 do IBGE e altimetria SRTM de 30 m,
baixados à parte, como descreve o `grafos/README.md`.
