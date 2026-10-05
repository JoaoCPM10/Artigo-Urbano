const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  ImageRun, Header, Footer, convertMillimetersToTwip
} = require("docx");

const CM = 566.929; // twips per cm
const FONT = "Georgia";

// ---- estilos base -----------------------------------------------------
function bodyPara(children, opts = {}) {
  return new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 120, ...(opts.spacing || {}) },
    children: Array.isArray(children) ? children : [new TextRun({ text: children, font: FONT, size: 20 })],
  });
}
function run(text, extra = {}) { return new TextRun({ text, font: FONT, size: 20, ...extra }); }
function ital(text) { return run(text, { italics: true }); }
function mono(text) { return run(text, { font: "Courier New" }); }

function heading1(num, text) {
  return new Paragraph({
    spacing: { before: 360, after: 120 },
    children: [new TextRun({ text: `${num}. ${text}`, font: FONT, size: 22, bold: true })],
  });
}
function heading2(num, text) {
  return new Paragraph({
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text: `${num}. ${text}`, font: FONT, size: 20, bold: true })],
  });
}
function tableCaption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 240, after: 120 },
    children: [new TextRun({ text, font: FONT, size: 18, bold: true })],
  });
}
function figCaption(text) {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 240 },
    children: [new TextRun({ text, font: FONT, size: 18 })],
  });
}
function refPara(text) {
  return new Paragraph({
    indent: { left: 397, hanging: 397 },
    spacing: { after: 120 },
    children: [new TextRun({ text, font: FONT, size: 20 })],
  });
}

// ---- figuras ------------------------------------------------------------
const FIGDIR = "Figures/";
function imgPara(file, w, h, caption) {
  const data = fs.readFileSync(FIGDIR + file);
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 240, after: 0 },
      children: [new ImageRun({ type: "png", data, transformation: { width: w, height: h } })],
    }),
    figCaption(caption),
  ];
}

// ---- tabela genérica ------------------------------------------------------
function mkTable(header, rows, colWidths) {
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);
  const mkCell = (text, bold) => new TableCell({
    width: { size: colWidths[0], type: WidthType.DXA },
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: String(text), font: FONT, size: 18, bold: !!bold })],
    })],
  });
  const headerRow = new TableRow({
    children: header.map((h, i) => new TableCell({
      width: { size: colWidths[i], type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: "E8E8E8" },
      children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: h, font: FONT, size: 18, bold: true })],
      })],
    })),
  });
  const bodyRows = rows.map(r => new TableRow({
    children: r.map((c, i) => new TableCell({
      width: { size: colWidths[i], type: WidthType.DXA },
      children: [new Paragraph({
        alignment: i === 0 ? AlignmentType.LEFT : AlignmentType.CENTER,
        children: [new TextRun({ text: String(c), font: FONT, size: 18 })],
      })],
    })),
  }));
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [headerRow, ...bodyRows],
  });
}

// =========================================================================
// CONTEÚDO
// =========================================================================
const TITLE_PT = "A Estrutura Dirigida Revela um Gargalo de Acesso que Escapa à Análise Não Dirigida: um Estudo em Grafos de Três Bairros do Rio de Janeiro";
const TITLE_EN = "Directed Structure Reveals an Access Bottleneck that Undirected Analysis Misses: A Graph Study of Three Rio de Janeiro Neighbourhoods";

const RESUMO_PT = "Este estudo exploratório modela as redes viárias de três bairros do Rio de Janeiro como grafos dirigidos e ponderados a partir do OpenStreetMap, perguntando se a estrutura dirigida revela um gargalo de acesso que a análise não dirigida deixa passar, e se isso reflete geografia, não tamanho. Comparamos uma península compacta (Urca) com duas grandes malhas abertas de orla (Copacabana e Botafogo), com as três redes recortadas pelo mesmo polígono administrativo oficial, usando conectividade, caminhos mínimos, centralidade de intermediação e fluxo máximo. Os indicadores estruturais dirigidos (pontes e articulações fortes) não ordenam os casos ao longo de um eixo de gargalo: a Urca fica entre as duas malhas em pontes fortes, e estas diferem bastante entre si. O corte mínimo entre dois nós satura em um em toda parte; um fluxo máximo até as portas de acesso administrativas reais de cada bairro, por sua vez, ordena os casos: uma rota disjunta para a Urca, dezoito para Copacabana, quinze para Botafogo, ordem que se mantém com o recorte por retângulo e sob variações da margem de fronteira. O gargalo é específico da geografia da península, não do tamanho, e não se generaliza para bairros grandes. Código e dados são abertos.";

const ABSTRACT_EN = "This exploratory study models the street networks of three Rio de Janeiro neighbourhoods as directed, weighted graphs from OpenStreetMap, asking whether directed structure reveals an access bottleneck that undirected analysis misses, and whether it reflects geography rather than size. We compare a compact peninsula (Urca) with two large, open beachfront grids (Copacabana and Botafogo), with all three networks clipped to the same official administrative polygon, using connectivity, shortest paths, betweenness centrality, and maximum flow. The directed structural indicators (strong bridges and articulation points) do not order the cases along a bottleneck axis: Urca falls between the two grids on strong bridges, and the grids differ considerably from each other. Node-to-node minimum cut saturates at one everywhere; a maximum flow from each core to its real administrative gateways instead orders the cases: one street-disjoint route for Urca, eighteen for Copacabana, fifteen for Botafogo, an ordering that holds under a bounding-box clip and under variations of the boundary margin. The bottleneck is specific to the peninsula's geography, not its size, and does not generalise to large neighbourhoods. Code and data are open.";

function frontMatter() {
  const items = [];
  items.push(new Paragraph({
    spacing: { after: 240 },
    children: [new TextRun({ text: TITLE_PT, font: FONT, size: 28, bold: true })],
  }));
  items.push(bodyPara([run("Autor(es) Anônimo(s)", { italics: true })]));
  items.push(bodyPara([run("Afiliação omitida para revisão duplo-cega", { italics: true })]));
  items.push(bodyPara([run("DOI: a atribuir pelos editores", { size: 18 })]));

  items.push(new Paragraph({
    indent: { left: 567, right: 567 },
    spacing: { before: 240, after: 120 },
    alignment: AlignmentType.JUSTIFIED,
    children: [run("Resumo: ", { bold: true, size: 18 }), run(RESUMO_PT, { size: 18 })],
  }));
  items.push(new Paragraph({
    indent: { left: 567, right: 567 },
    spacing: { after: 240 },
    children: [run("Palavras-chave: ", { bold: true, size: 18 }),
      run("Mobilidade urbana; Grafos dirigidos; Conectividade forte; Centralidade de intermediação; Fluxo máximo.", { size: 18 })],
  }));

  items.push(new Paragraph({
    spacing: { before: 240, after: 240 },
    children: [new TextRun({ text: TITLE_EN, font: FONT, size: 28, bold: true })],
  }));
  items.push(new Paragraph({
    indent: { left: 567, right: 567 },
    spacing: { after: 120 },
    alignment: AlignmentType.JUSTIFIED,
    children: [run("Abstract: ", { bold: true, size: 18 }), run(ABSTRACT_EN, { size: 18 })],
  }));
  items.push(new Paragraph({
    indent: { left: 567, right: 567 },
    spacing: { after: 360 },
    children: [run("Keywords: ", { bold: true, size: 18 }),
      run("Urban mobility; Directed graphs; Strong connectivity; Betweenness centrality; Maximum flow.", { size: 18 })],
  }));
  return items;
}

function introducao() {
  return [
    heading1(1, "Introdução"),
    bodyPara("Redes viárias são naturalmente modeladas como grafos cujos vértices são interseções e cujas arestas são trechos de rua. A direção do modelo importa: a regulamentação de mão única pode deixar uma interseção alcançável sem oferecer caminho de volta, distinção que um modelo não dirigido é incapaz de expressar. Este artigo é um estudo exploratório que caracteriza as redes viárias de três bairros do Rio de Janeiro e testa uma única pergunta norteadora: a estrutura dirigida revela um gargalo de acesso que a visão não dirigida deixa passar, e esse gargalo é uma propriedade da geografia do bairro, e não do seu tamanho?"),
    bodyPara("Para separar geografia de tamanho, comparamos um bairro compacto e geograficamente restrito, a Urca (uma península alcançada a partir do restante da cidade por um único corredor), com duas grandes malhas abertas de orla, Copacabana e Botafogo. As duas malhas grandes funcionam como casos de comparação: se o padrão da Urca fosse apenas um artefato de sua pequena escala, os indicadores acompanhariam o tamanho; se a origem for geográfica, a Urca deve se destacar das duas malhas grandes. Copacabana é de particular interesse porque seu acesso ao restante da cidade é popularmente associado a um pequeno número de túneis, o que a torna uma candidata plausível a um gargalo estrutural severo."),
    bodyPara("Além da questão algorítmica, o fluxo de acesso tem uma leitura prática direta: o número de rotas independentes que um bairro perderia antes de se tornar inalcançável por via terrestre, útil ao planejar diante de uma enchente, um deslizamento ou a interdição de um túnel."),
    bodyPara("As contribuições deste trabalho são: (i) um pipeline totalmente reprodutível que constrói grafos viários dirigidos e ponderados a partir do OpenStreetMap, confere sua extensão em relação a fronteiras administrativas oficiais e analisa sua conectividade, centralidade e fluxo; (ii) uma caracterização comparativa de três bairros reais, mostrando que os indicadores estruturais tradicionais não os distinguem ao longo de um eixo de gargalo; e (iii) um fluxo máximo do núcleo de cada bairro até suas portas de acesso administrativas reais que os distingue, diferente do corte mínimo entre dois nós. Mantemos deliberadamente a análise restrita a n = 3 casos contrastantes e interpretamos os resultados como ilustrativos, não como uma afirmação estatisticamente generalizável."),
  ];
}

function trabalhosRelacionados() {
  return [
    heading1(2, "Trabalhos Relacionados"),
    bodyPara("Extrair um grafo roteável a partir do OpenStreetMap e simplificar sua topologia (contraindo os pontos de forma que são meras curvas de uma rua em arestas únicas entre interseções verdadeiras) é prática consolidada, popularizada por ferramentas como o OSMnx (Boeing, 2017); seguimos a mesma construção e simplificação em um pipeline compacto e reprodutível, verificado em relação à biblioteca networkx."),
    bodyPara("A conectividade dispõe de um ferramental clássico para grafos não dirigidos: pontes e pontos de articulação, calculados em tempo linear pela busca em profundidade de Tarjan (1972), identificam as arestas e os vértices cuja remoção desconecta a rede. Essas primitivas respondem se dois pontos permanecem mutuamente alcançáveis quando uma rua é fechada, mas são cegas à direção. Italiano et al. (2012) as generalizaram para grafos dirigidos como pontes fortes e pontos de articulação fortes, cuja remoção aumenta o número de componentes fortemente conexas, e propuseram algoritmos de tempo linear; as noções fortes captam se é possível ir e voltar, não apenas alcançar."),
    bodyPara("Essa distinção não é apenas teórica para redes viárias, nas quais a regulamentação de mão única é predominante (74-91% dos trechos em nossos casos). Ferramentas como o OSMnx (Boeing, 2017) constroem grafos viários dirigidos, mas estudos de conectividade e resiliência costumam reduzi-los ao grafo não dirigido ou a resumos topológicos agregados (Corcoran & Jones, 2021), confundindo “alcançável” com “alcançável e capaz de retornar” e ocultando o efeito da direção. Aplicamos as noções fortes a bairros reais, apresentamos lado a lado os retratos fraco (não dirigido) e forte, e quantificamos o quanto o núcleo fortemente conexo se reduz sob a direção, uma lacuna que a análise não dirigida não é capaz de enxergar. Privilegiamos a transparência em detrimento da complexidade assintótica: em vez do algoritmo de tempo linear de Italiano, recalculamos as componentes fortes após a remoção de cada elemento candidato, restritas ao núcleo forte gigante, o que roda em segundos nessa escala (dezenas a algumas centenas de interseções), uma escolha de simplicidade, não uma alegação de escalabilidade."),
    bodyPara("Um amplo conjunto de trabalhos localiza pontos críticos em redes viárias por meio de centralidade, sobretudo a de intermediação (Kirkley et al., 2018; Halavachou & Li, 2021), e por meio de modelos de gargalos viários (Stepanchuk et al., 2020). Uma tradição bem mais antiga, a sintaxe espacial (space syntax), lê a acessibilidade a partir de medidas configuracionais como integração e escolha, calculadas sobre o mapa axial ou de segmentos de um assentamento (Hillier & Hanson, 1984). Ambas as tradições resumem uma rede a um único escore por vértice; nenhuma delas responde diretamente quantas rotas independentes ligam duas regiões, a pergunta que importa antes de fechar uma rua. Nós, em vez disso, lemos os gargalos por meio de fluxo máximo / corte mínimo, que conta explicitamente as rotas disjuntas por ruas e é comparável, em espírito, a qualquer uma das abordagens agregadas, ainda que com granularidade mais grosseira."),
    bodyPara("A resiliência de redes urbanas tem sido estudada como a degradação do serviço sob falha. Ganin et al. (2017), em quarenta áreas urbanas dos Estados Unidos, constatam que eficiência e resiliência variam de forma independente; nossa comparação não permite testar isso diretamente, mas é compatível: a Urca não é ineficiente, mas é, disparadamente, a mais frágil dos três casos. Avaliações baseadas em topologia simulam falhas aleatórias e direcionadas para classificar elementos críticos (Rouhana & Jawad, 2021; Alatrista-Salas et al., 2019); Ientile et al. (2022) formalizam um índice de perda de serviço; e uma abordagem topológica (Corcoran & Jones, 2021) descreve a forma das redes viárias. Medimos a resiliência de modo concreto, como o número de pares origem-destino que perdem toda a conexão quando um único elemento forte é removido, e relacionamos o custo de um desvio forçado à literatura sobre rotas alternativas (Silver et al., 2018). Diante desse panorama, a maioria das análises trata a rede como não dirigida ou a resume por meio de um escore agregado; poucas isolam o efeito da direção sobre a conectividade de acesso e o contrastam entre bairros de geografia distinta, que é a lacuna que este artigo explora."),
  ];
}

function metodologia() {
  const out = [heading1(3, "Metodologia"), heading2("3.1", "Dados e Construção do Grafo")];
  out.push(bodyPara([
    run("Para cada bairro, consultamos as vias trafegáveis ("), mono("highway"), run(" das classes "), ital("motorway"), run(" a "), ital("residential"), run(") dentro de um retângulo delimitador ("), ital("bounding box"), run(") junto à API Overpass do OpenStreetMap, e armazenamos em cache a resposta bruta para que a análise seja reprodutível "), ital("offline"), run(". Cada trecho de rua torna-se um arco dirigido que respeita sua "), ital("tag"), run(" "), mono("oneway"), run(": uma rua de mão dupla gera dois arcos opostos; uma rua de mão única, um único arco. Pontos de forma de grau dois são contraídos, de modo que os vértices sejam interseções verdadeiras e as arestas sejam as ruas entre elas; sem essa etapa, cada curva de uma rua se tornaria um falso ponto de articulação. As coordenadas são projetadas em metros, e cada aresta é ponderada por seu tempo de percurso, calculado a partir do comprimento e de uma velocidade padrão por classe de via quando o OpenStreetMap não informa "), mono("maxspeed"), run(". A Figura 1 ilustra a conversão do mapa para o grafo dirigido."),
  ]));
  out.push(...imgPara("fig_construction.png", 460, 217, "Figura 1 - Do mapa ao grafo dirigido: interseções tornam-se vértices e trechos de rua tornam-se arcos; uma rua de mão única gera um único arco (seta), uma rua de mão dupla gera dois arcos opostos."));
  out.push(bodyPara("Um retângulo delimitador traçado manualmente é uma escolha de modelagem, e constatamos que essa escolha tem consequências, que diferem de bairro para bairro. O retângulo de Copacabana foi originalmente traçado para manter seus dois túneis rodoviários como arestas internas, estendendo-se para o norte, além da fronteira administrativa com Botafogo. A conferência de cada interseção em relação ao polígono oficial do bairro (Instituto Pereira Passos [IPP], 2024) mostrou que 158 de suas 496 interseções, e 155 de seus trechos de rua, situavam-se, na verdade, dentro do território de Botafogo: as duas redes compartilhavam 143 interseções idênticas do OpenStreetMap. Em Urca e Botafogo ocorre o inverso: o polígono oficial é maior que o retângulo manual, e este truncava a rede em sua borda."));
  out.push(bodyPara("Para que nenhuma diferença entre os bairros decorra de um pré-processamento desigual, aplicamos a mesma regra aos três: o retângulo manual é usado apenas como envelope de busca, unido ao retângulo delimitador do próprio polígono oficial para garantir cobertura total, e o grafo resultante é recortado pelo polígono oficial antes de qualquer análise. A mesma fronteira define as portas de acesso (Seção 3.3). Todas as figuras e tabelas deste artigo refletem essas redes (Tabela 1); a Seção 4.6 compara o resultado com o retângulo manual sem recorte."));

  out.push(tableCaption("Tabela 1 - Redes após a simplificação topológica (OpenStreetMap), as três recortadas pelo polígono administrativo oficial do bairro"));
  out.push(mkTable(
    ["", "Urca", "Copacabana", "Botafogo"],
    [
      ["Interseções (V)", "70", "345", "434"],
      ["Trechos de rua", "104", "494", "563"],
      ["Trechos de mão única (%)", "91,3", "74,9", "76,2"],
      ["Núcleo fortemente conexo (V)", "65", "331", "392"],
      ["Fora do núcleo gigante (% de V)", "7,1", "4,1", "9,7"],
    ],
    [3200, 2000, 2200, 2000]
  ));
  out.push(new Paragraph({ spacing: { after: 240 }, children: [] }));

  out.push(bodyPara("A Figura 2 mostra as três redes após a simplificação, distinguindo trechos de mão única e de mão dupla. As duas malhas residenciais da Urca, unidas por um único corredor, ficam visíveis em contraste com as grandes malhas abertas de Copacabana e Botafogo; esse corredor é a constrição de acesso analisada na Seção 4."));
  out.push(...imgPara("fig_networks.png", 460, 168, "Figura 2 - As três redes dos bairros após a simplificação topológica e o recorte pelo polígono oficial (mão única em escuro, mão dupla em laranja). A Urca é uma península compacta cujas duas malhas se encontram em um único corredor; Copacabana e Botafogo são grandes malhas abertas."));

  out.push(heading2("3.2", "Conectividade, Caminhos Mínimos e Fluxo"));
  out.push(bodyPara("Todas as análises são executadas sobre um grafo dirigido e ponderado, representado por lista de adjacência, e nossas implementações foram verificadas em relação à biblioteca networkx. Componentes conexas não dirigidas e componentes fortemente conexas dirigidas (CFC) são encontradas por busca em largura, esta última pela interseção do conjunto alcançável no grafo com o conjunto alcançável em seu reverso. Pontes e pontos de articulação fracos são calculados diretamente a partir de sua definição, removendo o elemento e recontando as componentes não dirigidas. Pontes e pontos de articulação fortes são obtidos de modo análogo no cenário dirigido: um elemento é forte quando sua remoção divide o núcleo fortemente conexo gigante em mais de uma CFC, seguindo as definições de Italiano et al. (2012). Os caminhos mínimos usam o algoritmo de Dijkstra (1959) com heap binário, verificado de forma independente pelo algoritmo de Bellman-Ford (Bellman, 1958); uma rota alternativa é o caminho mínimo recalculado após o bloqueio de um trecho (Seção 4.5). O fluxo máximo e o corte mínimo usam o algoritmo de Edmonds-Karp (Edmonds & Karp, 1972) com capacidade unitária por rua, de modo que o fluxo máximo entre dois pontos seja igual ao número de rotas disjuntas por ruas entre eles, e o corte mínimo seja o menor conjunto de ruas cujo fechamento os separa. A centralidade de intermediação é calculada com o algoritmo de Brandes (2001) sobre o grafo dirigido, ponderando os caminhos mínimos pelo tempo de percurso, de modo que o escore de um vértice seja a fração dos pares origem-destino de tempo mínimo que passam por ele."));

  out.push(heading2("3.3", "Fluxo de Acesso por Portas"));
  out.push(bodyPara("O corte mínimo entre duas interseções isoladas satura em um nas três redes (Seção 4): como as malhas de mão única densa contêm pontes não dirigidas por quase toda parte, quase todo par origem-destino é separado por uma única aresta próxima a uma das extremidades, bem antes de qualquer constrição geográfica."));
  out.push(bodyPara([
    run("Para medir o acesso ao restante da cidade, em vez de uma travessia interna arbitrária, distinguimos o "), ital("interior"), run(" de um bairro de suas "), ital("portas de acesso"), run(" ("), ital("gateways"), run("). Cada rede viária é extraída com uma pequena margem além da própria fronteira do bairro (seu polígono oficial, nos três casos), suficiente para incluir a primeira interseção além da fronteira em toda rua que a cruze. Um vértice é uma porta de acesso se pelo menos uma de suas arestas incidentes cruza essa fronteira; todo outro vértice é interior. O conjunto de portas de acesso é, portanto, o conjunto de pontos pelos quais é fisicamente possível deixar o bairro, e não um marco interno escolhido por uma heurística de distância. Como uma porta de acesso pode admitir tráfego em apenas um sentido, restringimos o interior e o conjunto de portas de acesso ao maior componente não dirigido do bairro, e não ao seu núcleo fortemente conexo: uma saída de mão única ainda é uma saída real."),
  ]));
  out.push(bodyPara("A região de origem é a fração f (f = 0,2) das interseções interiores mais distantes, em número de arestas, da porta de acesso mais próxima, ou seja, o núcleo do bairro. Uma superfonte alimenta a região de origem, e o conjunto completo de portas de acesso alimenta um superssumidouro, ambos com capacidade infinita, e o algoritmo de Edmonds-Karp é executado entre eles sobre a rede de capacidade unitária. O valor resultante, que chamamos de fluxo de acesso, é o número de rotas disjuntas por ruas entre o núcleo do bairro e suas saídas reais para o restante da cidade (Seção 4.3); esse valor é estável para f entre 0,15 e 0,25 e para uma margem de busca de fronteira entre 200 e 800 m, nos três bairros."));
  out.push(bodyPara("Isso substitui uma definição anterior, construída a partir de dois polos internos encontrados por uma varredura dupla do grafo, que media a travessia mais estreita ao longo do eixo mais alongado do bairro mas nunca fazia referência à sua fronteira real; mantemos essa construção apenas como verificação interna de que a região de origem e o conjunto de portas de acesso nunca se sobrepõem."));
  return out;
}

function resultados() {
  const out = [heading1(4, "Resultados"), heading2("4.1", "Os Indicadores Estruturais Não Separam os Casos")];
  out.push(bodyPara("A Tabela 2 apresenta os indicadores estruturais dirigidos como proporções, já que as contagens brutas não são comparáveis entre redes de tamanhos tão diferentes. Eles não formam um eixo de gargalo. A Urca tem a maior proporção de articulações fortes (73,8%), mas em pontes fortes (61,5%) fica entre Copacabana (45,3%) e Botafogo (68,4%), e tem a menor proporção de pontes fracas (10,6%, contra 15,8% e 20,2%). As duas malhas abertas, por sua vez, diferem bastante entre si: Botafogo tem consideravelmente mais pontes fortes e articulações fortes (68,4% e 63,5%) do que Copacabana (45,3% e 54,1%). Essa diferença persiste quando as três redes são construídas com o retângulo manual em vez do polígono (Seção 4.6), portanto não decorre do pré-processamento. A Figura 3 mostra, para a Urca, que os elementos fortes se distribuem por todo o núcleo (59 das 96 ruas do núcleo são pontes fortes), nas duas malhas residenciais e no corredor que as liga, e não em um único ponto de acesso. As proporções, portanto, não separam os casos ao longo de um eixo de gargalo, um contraste desenvolvido na Seção 5."));

  out.push(tableCaption("Tabela 2 - Indicadores estruturais dirigidos (normalizados), com as três redes recortadas pelo polígono oficial"));
  out.push(mkTable(
    ["", "Urca", "Copacabana", "Botafogo"],
    [
      ["Pontes fracas (% dos trechos)", "10,6", "15,8", "20,2"],
      ["Pontes fortes (% das ruas do núcleo)", "61,5", "45,3", "68,4"],
      ["Articulações fortes (% do núcleo)", "73,8", "54,1", "63,5"],
    ],
    [3200, 2000, 2200, 2000]
  ));
  out.push(new Paragraph({ spacing: { after: 240 }, children: [] }));

  out.push(...imgPara("fig_urca_strong.png", 360, 360, "Figura 3 - Gargalos estruturais dirigidos na Urca: ruas cuja remoção fragmenta o núcleo fortemente conexo (pontes fortes) e interseções com a mesma propriedade (pontos de articulação fortes). Eles se distribuem por todo o núcleo, nas duas malhas residenciais e no corredor que as liga, e não em um único ponto de acesso."));

  out.push(heading2("4.2", "O Corte Mínimo Entre Dois Nós Satura"));
  out.push(bodyPara("Para uma origem e um destino bem conectados dentro do núcleo forte, o corte mínimo de Edmonds-Karp é igual a um nos três bairros. A única aresta de corte situa-se perto de uma das extremidades, e não em algum estrangulamento geográfico: como a rede não dirigida tem pontes por toda parte, um par origem-destino quase sempre tem uma única rua separadora próxima a ele. O corte mínimo entre dois nós é, portanto, pouco informativo sobre acesso; ele mede uma ponte local, não a conexão do bairro com o restante da cidade."));

  out.push(heading2("4.3", "O Fluxo de Acesso por Portas Separa os Casos"));
  out.push(bodyPara("O fluxo de acesso por portas da Seção 3.3 ordena os casos (Tabela 3). A Urca tem uma única rota disjunta por ruas entre seu núcleo e suas três portas de acesso reais ao restante da cidade. Copacabana oferece dezoito dessas rotas por meio de vinte e uma portas de acesso, e Botafogo, quinze por meio de trinta e uma. Os três valores são idênticos para f entre 0,15 e 0,25 e para uma margem de busca de fronteira entre 200 e 800 m, e as duas malhas abertas ficam uma ordem de grandeza acima da Urca em toda essa faixa. Esse é o único indicador que isola um gargalo de acesso, e ele não acompanha o tamanho: Botafogo (cerca de seis vezes maior que a Urca em interseções) e Copacabana (cerca de cinco vezes maior) oferecem ambos uma ordem de grandeza a mais de rotas do que a Urca. O acesso de Copacabana não se reduz a seus dois túneis: eles são apenas duas de suas vinte e uma portas de acesso, de modo que ruas de superfície sustentam a maior parte de suas dezoito rotas disjuntas."));

  out.push(tableCaption("Tabela 3 - Fluxo de acesso por portas: rotas disjuntas por ruas do núcleo de cada bairro até suas portas de acesso administrativas reais (f = 0,2)"));
  out.push(mkTable(
    ["", "Urca", "Copacabana", "Botafogo"],
    [
      ["Portas de acesso identificadas", "3", "21", "31"],
      ["Fluxo de acesso (rotas)", "1", "18", "15"],
      ["Intermediação máxima (% dos pares)", "54,2", "27,8", "22,4"],
      ["Interpretação", "corredor único", "malha aberta", "malha aberta"],
    ],
    [3200, 2000, 2200, 2000]
  ));
  out.push(new Paragraph({ spacing: { after: 240 }, children: [] }));


  out.push(heading2("4.4", "A Intermediação Se Concentra no Corredor da Urca"));
  out.push(bodyPara("A centralidade de intermediação dirigida, ponderada pelo tempo de percurso, é compatível com a leitura do fluxo de acesso nos três bairros (Figura 4). Na Urca, as cinco interseções mais centrais, todas ao longo do corredor que liga as duas malhas e em suas junções com elas, estão presentes em 45,8% a 54,2% de todos os pares origem-destino de tempo mínimo. Copacabana e Botafogo não têm vértices tão dominantes: suas interseções mais centrais alcançam 27,8% e 22,4%, respectivamente, com a carga distribuída ao longo de um eixo arterial em forma de Y em Copacabana e ao longo de eixos paralelos em Botafogo. O valor de Copacabana fica um pouco acima do de Botafogo, mais um indicador em que as duas malhas abertas não se acompanham exatamente (Seção 5). Reportamos o máximo, e não um índice de concentração, porque este último é confundido pelo tamanho do núcleo (um núcleo pequeno eleva a mediana e reduz a desigualdade independentemente da geografia); o máximo, já normalizado pelo número de pares, é comparável entre tamanhos distintos e volta a isolar a Urca."));
  out.push(...imgPara("fig_betweenness.png", 460, 166, "Figura 4 - Centralidade de intermediação dirigida (caminhos de tempo mínimo, núcleo forte). A intermediação da Urca se concentra ao longo do corredor de acesso e em suas junções; a carga de Copacabana se concentra ao longo de um eixo arterial em forma de Y, e a de Botafogo ao longo de eixos paralelos, ambos com um máximo bem mais baixo do que o da Urca."));

  out.push(heading2("4.5", "Resiliência do Núcleo Forte"));
  out.push(bodyPara("Medimos a resiliência de modo exaustivo, fechando cada ponte forte ou articulação forte por vez e contando, sobre todos os pares ordenados do núcleo, quantos perdem toda a conexão. Na Urca (4.160 pares do núcleo), a ponte forte mediana desconecta 250 pares, e a pior, 2.112; a articulação forte mediana desconecta 341,5, e a pior, 2.251. Em Copacabana (109.230 pares), a ponte forte mediana desconecta 660 pares, e a pior, 14.280; em Botafogo (153.272 pares), 782 e 12.818, respectivamente. A fração do núcleo isolada é maior na Urca (mediana de 6,0% para pontes fortes, contra 0,6% e 0,5% nas malhas grandes), mas isso é, em parte, um efeito de escala: um único elemento removido corta uma fatia maior de um núcleo pequeno, de modo que as contagens absolutas e o tamanho do núcleo na Tabela 1 devem ser lidos em conjunto. O ponto qualitativo é robusto: em todos os bairros, nenhuma ponte forte é inofensiva, a menos danosa ainda isola um número não trivial de pares, e o impacto de um elemento não é uma propriedade fixa, mas depende de qual par é considerado."));
  out.push(bodyPara("Além da conectividade binária, um desvio forçado tem um custo mensurável. Recalcular a rota mais curta após bloquear, ao longo dela, um trecho que não seja ponte aumenta o tempo de percurso em 13,6% na Urca, 5,1% em Copacabana e 1,8% em Botafogo. Essas mesmas rotas também atravessam trechos que são, eles próprios, pontes fortes (3, 4 e 6, respectivamente): fechar qualquer um deles não admite desvio algum, apenas a desconexão já quantificada acima. Esse indicador é o mais frágil do artigo: o par origem-destino é escolhido por uma heurística sobre o próprio grafo e muda com o recorte (em Botafogo, o acréscimo era de 6,0% com o retângulo manual), de modo que o lemos como ilustração, não como evidência."));

  out.push(heading2("4.6", "Sensibilidade ao Tipo de Recorte"));
  out.push(bodyPara("A Tabela 4 repete as medidas centrais com o retângulo manual, sem recorte e com a fronteira das portas de acesso definida pelo próprio retângulo, e com o polígono oficial (a versão usada no restante do artigo). O recorte pouco afeta Botafogo (pontes fortes de 70,4% para 68,4%; fluxo de acesso de 16 para 15), mas altera bastante os outros dois bairros. Em Copacabana, o retângulo incluía interseções de Botafogo, e o recorte reduz as pontes fortes de 53,1% para 45,3% e as portas de 45 para 21. Na Urca, o retângulo truncava a península, e o recorte leva o núcleo forte de 37 para 65 interseções e a fração de interseções fora dele de 38,3% para 7,1%. Duas conclusões seguem. Primeiro, a diferença de pontes fortes entre Copacabana e Botafogo não é efeito do pré-processamento desigual: ela existe nos dois recortes (53,1% contra 70,4% com o retângulo; 45,3% contra 68,4% com o polígono). Segundo, o fluxo de acesso separa os casos nos dois recortes (1 na Urca, contra 13 a 18 em Copacabana e 15 a 16 em Botafogo), e a intermediação máxima da Urca (52,2% a 54,2%) permanece a maior. Já a fração de interseções fora do núcleo forte da Urca e o número de portas dependem do recorte e devem ser lidos com cautela. Por isso a comparação principal usa o mesmo polígono nos três bairros."));
  out.push(tableCaption("Tabela 4 - Sensibilidade ao tipo de recorte. Retângulo: retângulo manual sem recorte, com as portas de acesso na borda do retângulo. Polígono: polígono oficial (versão do artigo). V: interseções; Fora: % de V fora do núcleo forte; Pontes: % de pontes fortes; Fluxo: fluxo de acesso (f = 0,2); Interm.: intermediação máxima (% dos pares)"));
  out.push(mkTable(
    ["Bairro", "Recorte", "V", "Fora", "Pontes", "Portas", "Fluxo", "Interm."],
    [
      ["Urca", "retângulo", "60", "38,3", "67,3", "4", "1", "52,2"],
      ["", "polígono", "70", "7,1", "61,5", "3", "1", "54,2"],
      ["Copacabana", "retângulo", "496", "19,6", "53,1", "45", "13", "30,2"],
      ["", "polígono", "345", "4,1", "45,3", "21", "18", "27,8"],
      ["Botafogo", "retângulo", "398", "14,3", "70,4", "28", "16", "22,5"],
      ["", "polígono", "434", "9,7", "68,4", "31", "15", "22,4"],
    ],
    [1500, 1300, 800, 900, 1000, 1000, 900, 1000]
  ));
  out.push(new Paragraph({ spacing: { after: 240 }, children: [] }));

  return out;
}

function discussao() {
  const out = [heading1(5, "Discussão")];
  out.push(bodyPara("Lidos em conjunto, os indicadores estruturais (pontes e articulações fortes) não ordenam os casos ao longo de um eixo de gargalo, e a Urca só se isola quando se olha o acesso. A Urca é o caso restrito: 91,3% de seus trechos são de mão única, mas essa direcionalidade retira apenas 7,1% de suas interseções do núcleo forte (contra 38,3% com o retângulo manual, que truncava a península), e uma única rota disjunta liga seu núcleo ao restante da cidade, com as interseções do corredor presentes em 46% a 54% de suas rotas de tempo mínimo. Copacabana e Botafogo são, ambos, casos abertos no sentido que importa para o acesso: nenhum deles se assemelha ao padrão de porta única da Urca, oferecendo dezoito e quinze rotas disjuntas por porta de acesso, respectivamente, e ambos têm uma proporção igualmente alta de trechos de mão única (74,9% e 76,2%). Não são, contudo, gêmeos estruturais: suas proporções de pontes fortes e articulações fortes (45,3% e 54,1% em Copacabana; 68,4% e 63,5% em Botafogo, Tabela 2) diferem bastante, e essa diferença existe com o recorte por polígono e com o retângulo (Seção 4.6). O gargalo de acesso permanece uma propriedade da geografia da Urca, uma península com um único corredor, e não se generaliza para um bairro grande de nenhum dos dois perfis."));
  out.push(bodyPara("O resultado mais contraintuitivo diz respeito a Copacabana. Seu acesso é popularmente associado a poucos túneis, o que a tornava uma candidata plausível a um gargalo estrutural severo. No entanto, nessa resolução, a reputação dos túneis não se traduz em um gargalo mensurável: das vinte e uma portas de acesso encontradas em sua fronteira oficial, os dois túneis são apenas parte da contagem, e ruas de superfície sustentam o restante de suas dezoito rotas disjuntas por porta de acesso até o restante da cidade. Uma leitura em três degraus, do tipo pequeno, grande e sem gargalo, não é, portanto, sustentada pelos dados; já um contraste em dois grupos, entre restrito e aberto, é."));
  out.push(bodyPara("Diversas ameaças à validade relativizam essas observações. O estudo baseia-se em n = 3 casos contrastantes e é ilustrativo, não estatisticamente geral. Comparar bairros de geografia distinta exige uma extensão espacial que é, ela própria, uma escolha de modelagem, e essa escolha não está isenta de risco: um retângulo traçado manualmente situava 158 das 496 interseções de Copacabana dentro do território oficial de Botafogo e truncava a rede da Urca e a de Botafogo (Seção 3.1). Adotamos a mesma fronteira oficial nos três bairros e mostramos o efeito da alternativa na Seção 4.6; ainda assim, a fronteira administrativa é uma escolha, porque um bairro não é necessariamente uma unidade de mobilidade, e as portas de acesso aqui são as do bairro, não as de uma região funcional. Consideramos a discrepância um alerta para qualquer estudo que defina um bairro por um retângulo traçado manualmente perto de uma fronteira compartilhada. A definição de porta de acesso depende de uma margem fixa de busca de fronteira, testada de 200 a 800 m nos três bairros sem alteração do fluxo de acesso. A capacidade unitária trata toda rua da mesma forma, ignorando largura e número de faixas; os tempos de percurso apoiam-se em velocidades padrão onde o OpenStreetMap não informa nenhuma; os resultados de conectividade dependem diretamente da qualidade das tags oneway, densas nesses bairros (até 91,3% dos trechos da Urca) e, portanto, consequentes; e o máximo de intermediação da Tabela 3 ainda não foi conferido contra um modelo nulo, de modo que não podemos descartar que parte da diferença entre a Urca e as duas malhas abertas reflita o tamanho do núcleo, e não apenas a geografia (Seção 4.4). A Figura 5 resume os indicadores normalizados."));
  out.push(...imgPara("fig_comparison.png", 460, 239, "Figura 5 - Indicadores estruturais normalizados por bairro, com as três redes recortadas pelo polígono oficial. As proporções estruturais não ordenam os casos ao longo de um eixo de gargalo; o fluxo de acesso da Tabela 3 é o que isola a porta única da Urca."));
  return out;
}

function conclusao() {
  return [
    heading1(6, "Conclusões"),
    bodyPara("Os indicadores estruturais tradicionais, pontes fortes e pontos de articulação fortes, não separam os casos ao longo de um eixo de gargalo: a Urca fica entre as duas malhas abertas em pontes fortes, e as duas malhas diferem bastante entre si, resultado que se mantém com o recorte por polígono oficial e com o retângulo manual. O corte mínimo entre dois nós é pouco informativo aqui, saturando em um porque malhas de mão única densa contêm pontes não dirigidas por quase toda parte. O sinal distintivo vem de um fluxo máximo entre o núcleo de cada bairro e suas portas de acesso administrativas reais: a península se conecta ao restante da cidade por uma única rota disjunta por ruas, enquanto Copacabana oferece dezoito, e Botafogo, quinze, ordem estável sob variações do recorte, da margem de fronteira e da região de origem. Um desvio forçado ao redor de uma rua fechada também custa mais na Urca (13,6% a mais de tempo de percurso) do que nas malhas abertas (5,1% e 1,8%), embora esse indicador dependa do par origem-destino escolhido. O gargalo de acesso é, assim, uma propriedade da geografia da península, e não se generaliza para bairros grandes, nem mesmo para um conhecido pela restrição de acesso por túneis. Essas observações baseiam-se em n = 3 casos contrastantes e são ilustrativas, não estatisticamente gerais; estender a comparação a mais bairros, correlacionar o fluxo de acesso com um índice geométrico de forma, e conferir o máximo de intermediação contra um modelo nulo (Seção 5) ficam para trabalhos futuros."),
    bodyPara([run("Reprodutibilidade: ", { bold: true }), run("Todo o código-fonte e os dados estão abertamente disponíveis (repositório omitido para a revisão duplo-cega).")]),
  ];
}

function referencias() {
  const refs = [
    "Alatrista-Salas, H., Núñez del Prado Cortez, M., & Rodríguez-López, G. (2019). Robustness of densely populated urban networks in relation to the spread of traffic. Revista Internacional de Tecnología, Ciencia y Sociedad, 8(1), 1-10.",
    "Bellman, R. (1958). On a routing problem. Quarterly of Applied Mathematics, 16, 87-90.",
    "Boeing, G. (2017). OSMnx: New methods for acquiring, constructing, analyzing, and visualizing complex street networks. Computers, Environment and Urban Systems, 65, 126-139. https://doi.org/10.1016/j.compenvurbsys.2017.05.004",
    "Brandes, U. (2001). A faster algorithm for betweenness centrality. The Journal of Mathematical Sociology, 25(2), 163-177. https://doi.org/10.1080/0022250X.2001.9990249",
    "Corcoran, P., & Jones, C. B. (2021). A persistent homology model of street network connectivity. Transactions in GIS. https://doi.org/10.1111/tgis.12844",
    "Dijkstra, E. W. (1959). A note on two problems in connexion with graphs. Numerische Mathematik, 1, 269-271.",
    "Edmonds, J., & Karp, R. M. (1972). Theoretical improvements in algorithmic efficiency for network flow problems. Journal of the ACM, 19(2), 248-264.",
    "Ganin, A. A., Kitsak, M., Marchese, D., Keisler, J. M., Seager, T., & Linkov, I. (2017). Resilience and efficiency in transportation networks. Science Advances, 3(12), e1701079.",
    "Halavachou, Y., & Li, J. (2021). Uncovering correlations between urban road network centrality and human mobility. International Journal of Advanced Network, Monitoring and Controls, 6(4), 99-112.",
    "Hillier, B., & Hanson, J. (1984). The social logic of space. Cambridge University Press.",
    "Ientile, S., Bianne, G., Chevalier, C., Schmidt, F., Rasol, M., Orcesi, A., Adelaide, L., & Nedjar, B. (2022). Measuring road network resilience by loss of serviceability index for critical road links. Proceedings of the Institution of Civil Engineers - Bridge Engineering, 175(3), 160-173.",
    "Instituto Pereira Passos (IPP). (2024). Limite de bairros [Conjunto de dados]. Data.Rio. https://www.data.rio/datasets/PCRJ::limite-de-bairros/about",
    "Italiano, G. F., Laura, L., & Santaroni, F. (2012). Finding strong bridges and strong articulation points in linear time. Theoretical Computer Science, 447, 74-84.",
    "Kirkley, A., Barbosa, H., Barthelemy, M., & Ghoshal, G. (2018). From the betweenness centrality in street networks to structural invariants in random planar graphs. Nature Communications, 9(1), 2501.",
    "Rouhana, F., & Jawad, D. (2021). Transportation network resilience against failures: GIS-based assessment of network topology role. International Journal of Disaster Resilience in the Built Environment.",
    "Silver, G., Akbarzadeh, M., & Estrada, E. (2018). Tuned communicability metrics in networks. The case of alternative routes for urban traffic. Chaos, Solitons & Fractals, 116, 402-413.",
    "Stepanchuk, O., Bieliatynskyi, A., & Pylypenko, O. (2020). Modelling the bottlenecks interconnection on the city street network. In VIII International Scientific Siberian Transport Forum (TransSiberia 2019) (Advances in Intelligent Systems and Computing, Vol. 1116). Springer.",
    "Tarjan, R. (1972). Depth-first search and linear graph algorithms. SIAM Journal on Computing, 1(2), 146-160.",
  ];
  return [heading1(7, "Referências"), ...refs.map(refPara)];
}

// =========================================================================
const doc = new Document({
  sections: [{
    properties: {
      page: {
        size: { width: convertMillimetersToTwip(210), height: convertMillimetersToTwip(297) },
        margin: { top: 3685, bottom: 3118, left: 2268, right: 2268 },
      },
    },
    children: [
      ...frontMatter(),
      ...introducao(),
      ...trabalhosRelacionados(),
      ...metodologia(),
      ...resultados(),
      ...discussao(),
      ...conclusao(),
      ...referencias(),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync("artigo_risti_pt.docx", buf);
  console.log("gerado: artigo_risti_pt.docx");
});
