# -*- coding: utf-8 -*-
"""Geometria e listas do popup radial - funções puras, sem Qt e sem leitura
de configuração, separadas de `menu_radial_qt.py` pra serem testáveis sem
display (`testes/testar_geometria.py`).

Ângulo 0° = 3h (leste), crescendo ANTI-horário (convenção do Qt); item 0 no
topo (90°), os seguintes em sentido HORÁRIO (ângulo decrescente).

O raio de cada nível é calculado (não fixo em 2 constantes) pra suportar
categorias aninhadas dentro de categorias. Nível 0 = anel de favoritos
(sempre visível); nível 1, 2, 3... = cada categoria aberta a partir do nível
anterior."""
import math
import unicodedata

RAIO_INTERNO = 68          # borda interna do anel de favoritos / raio do centro
RAIO_EXTERNO_1 = 176       # borda externa do anel de favoritos (nível 0, sempre visível)
GAP_ENTRE_ANEIS = 18       # folga visual entre um anel e o próximo
LARGURA_ANEL_SUBITENS = 110  # espessura de cada anel ALÉM do primeiro
MAX_NIVEIS_ANINHADOS = 4   # favoritos (nível 0) + até 3 categorias aninhadas
MARGEM = 80

# Fatia de paginação - sentinela puramente de UI (não é persistido), gerada
# por `paginar` sempre que uma camada não cabe inteira no limite configurado.
ITEM_MAIS_PAGINA = "▸ Mais"


def raio_interno_nivel(indice_nivel):
    if indice_nivel <= 0:
        return RAIO_INTERNO
    raio = RAIO_EXTERNO_1
    for _ in range(indice_nivel - 1):
        raio += GAP_ENTRE_ANEIS + LARGURA_ANEL_SUBITENS
    return raio + GAP_ENTRE_ANEIS


def raio_externo_nivel(indice_nivel):
    if indice_nivel <= 0:
        return RAIO_EXTERNO_1
    return raio_interno_nivel(indice_nivel) + LARGURA_ANEL_SUBITENS


def tamanho_para_profundidade(profundidade):
    """profundidade = quantos anéis além do de favoritos estão abertos AGORA -
    o popup só ocupa na tela o espaço que precisa neste momento."""
    return raio_externo_nivel(profundidade) * 2 + MARGEM


def margem_ancora_que_cabe(dimensao_tela, profundidade_desejada):
    """Quanto de margem reservar num eixo pro popup nunca precisar "pular"
    de lugar ao crescer até `profundidade_desejada` - se isso não couber em
    metade da tela (comum no eixo Y de monitores widescreen), recua pra
    profundidades menores até achar uma que caiba; no pior caso usa só o
    tamanho de favoritos, aceitando que aninhar bem fundo perto da borda pode
    cortar um pouco, em troca do popup abrir onde o cursor está."""
    for profundidade in range(profundidade_desejada, -1, -1):
        margem = tamanho_para_profundidade(profundidade) // 2
        if margem <= dimensao_tela // 2:
            return margem
    return tamanho_para_profundidade(0) // 2


def angulo_item(indice, capacidade, referencia=90.0):
    """Ângulo central da fatia `indice` - `referencia` é onde a fatia 0 fica
    (90° = topo, padrão do anel de favoritos). Um anel aberto a partir de uma
    categoria usa outra referência, pra ficar centrado em volta do botão que
    o abriu."""
    passo = 360.0 / capacidade
    return (referencia - indice * passo) % 360


def indice_da_fatia(angulo, capacidade, referencia=90.0):
    """Cada fatia é DESENHADA centrada em `angulo_item` - o hit-test usa
    `round()` (não `floor()`) pra centralizar a área clicável no mesmo ponto
    que o desenho usa."""
    passo = 360.0 / capacidade
    deslocado = (referencia - angulo) % 360
    return round(deslocado / passo) % capacidade


def fatia_no_anel(dx, dy, raio_min, raio_max, capacidade, quantidade_real, referencia=90.0):
    """O TAMANHO de cada fatia (`capacidade`, o limite configurado daquele
    anel) é fixo, independente de quantos itens existem agora
    (`quantidade_real`). Um clique/hover numa posição "vazia" (índice >=
    quantidade_real) não acerta nada."""
    distancia = math.hypot(dx, dy)
    if distancia > raio_max or distancia < raio_min:
        return None
    angulo = math.degrees(math.atan2(-dy, dx)) % 360
    indice = indice_da_fatia(angulo, capacidade, referencia)
    return indice if indice < quantidade_real else None


def paginar(lista, pagina, limite):
    """Quando não cabe tudo numa página, a ÚLTIMA posição vira
    `ITEM_MAIS_PAGINA` (avança a página, com wraparound), reservando 1 vaga
    real a menos por página pra o total de fatias visíveis nunca passar do
    limite. Devolve (itens_da_pagina, pagina_normalizada, total_paginas)."""
    if len(lista) <= limite:
        return lista, 0, 1
    tamanho_pagina = max(1, limite - 1)
    total_paginas = math.ceil(len(lista) / tamanho_pagina)
    pagina = pagina % total_paginas
    inicio = pagina * tamanho_pagina
    pagina_atual = lista[inicio:inicio + tamanho_pagina]
    pagina_atual.append(ITEM_MAIS_PAGINA)
    return pagina_atual, pagina, total_paginas


def dividir_icone_rotulo(rotulo):
    """"📁 Jogos" -> ("📁", "Jogos"); "calculadora" -> (None, "calculadora")."""
    partes = rotulo.split(" ", 1)
    if partes[0] and ord(partes[0][0]) > 127:
        return partes[0], (partes[1] if len(partes) > 1 else "")
    return None, rotulo


def normalizar_busca(texto):
    """Minúsculas e sem acento: "Cálculo" e "calculo" batem."""
    decomposto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in decomposto if not unicodedata.combining(c)).lower()


def corresponde_busca(consulta, *textos):
    """True se `consulta` (já digitada pelo usuário) aparece em algum dos
    textos, ignorando acento e maiúsculas."""
    q = normalizar_busca(consulta)
    return any(q in normalizar_busca(t) for t in textos if t)
