"""Converte a licao no texto de acompanhamento (markdown -> PDF).

Mesma fonte de dados do audio: o YAML da licao. Texto e MP3 nao podem divergir,
e a unica forma de garantir isso e nao ter duas fontes.

Por que o texto existe: o Dr. Victor le em B1 e ouve abaixo disso (medido em
12/08/2026). Sem o texto, a frase que ele nao pegar caminhando fica perdida.
A ordem de uso importa e vai impressa no proprio documento -- ler ANTES de
escutar transforma o treino de ouvido em leitura com trilha sonora.
"""

from __future__ import annotations

from .licao import Bloco, Licao

_ABERTURA = """---
title: "{titulo}"
subtitle: "Lição {id} · nível {nivel}"
lang: fr
---

> **Escute primeiro, leia depois.** Ler antes de escutar troca o treino de
> ouvido por leitura com trilha sonora — e a escuta é justamente o que precisa
> de treino.

## A cena

"""


def como_markdown(licao: Licao) -> str:
    """Devolve o texto de acompanhamento em markdown, pronto para o pandoc."""
    partes = [_ABERTURA.format(titulo=licao.titulo, id=licao.id, nivel=licao.nivel)]

    for linha in licao.cena:
        partes.append(f"— *{linha}*\n\n")

    for bloco in licao.blocos:
        partes.append(_SECOES[bloco.tipo](bloco))

    return "".join(partes)


def _decomposicao(bloco: Bloco) -> str:
    linhas = ["\n## Frase a frase\n\n"]
    for item in bloco.itens:
        linhas.append(f"**{item['fr']}**\n\n")
        linhas.append(f"{item['pt']}\n\n")
    return "".join(linhas)


def _semaforo(bloco: Bloco) -> str:
    """O par erro/acerto, que no audio e etiqueta falada e aqui e contraste visual."""
    linhas = ["\n## O que muda\n\n"]
    for item in bloco.itens:
        # Travessao, nao dois-pontos: o documento declara `lang: fr`, e o pandoc
        # aplica a regra francesa de espaco fino antes de `:` `?` `!`. Isso deixa
        # o frances tipograficamente certo ("le film ?") e a prosa portuguesa
        # errada ("Nao se diz :"). O travessao funciona nos dois idiomas.
        linhas.append(f"Não se diz — *{item['errado']}*\n\n")
        linhas.append(f"Diz-se — **{item['certo']}**\n\n")
        if item.get("nota_pt"):
            linhas.append(f"> {item['nota_pt']}\n\n")
    return "".join(linhas)


def _producao(bloco: Bloco) -> str:
    linhas = ["\n## Para responder sozinho\n\n"]
    for item in bloco.itens:
        linhas.append(f"**{item['pergunta']}**\n\n")
        linhas.append(f"{item['resposta']}\n\n")
    return "".join(linhas)


def _revisao(bloco: Bloco) -> str:
    linhas = ["\n## Da lição anterior\n\n"]
    for item in bloco.itens:
        linhas.append(f"**{item['fr']}** — {item['pt']}\n\n")
    return "".join(linhas)


_SECOES = {
    "decomposicao": _decomposicao,
    "semaforo": _semaforo,
    "producao": _producao,
    "revisao": _revisao,
}
