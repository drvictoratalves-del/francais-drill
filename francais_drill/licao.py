"""Carrega e valida a licao declarada em YAML.

Licao malformada falha ALTO, nomeando o campo. Nunca gerar MP3 parcial: um
audio truncado toca do inicio ao fim sem erro visivel, e o defeito so aparece
quando o aluno ja praticou em voz alta o que faltou.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

TIPOS_VALIDOS = ("decomposicao", "semaforo", "producao", "revisao")

# Campos que cada tipo de bloco EXIGE. `nota_pt` do semaforo e opcional: nem
# todo par erro/acerto precisa de explicacao, e forcar uma produz ruido.
CAMPOS_OBRIGATORIOS = {
    "decomposicao": ("fr", "pt"),
    "semaforo": ("errado", "certo"),
    "producao": ("pergunta", "resposta"),
    "revisao": ("fr", "pt"),
}

_CAMPOS_LICAO = ("id", "titulo", "nivel", "cena", "blocos")


class LicaoInvalidaError(ValueError):
    """Licao que nao pode virar audio. Sempre nomeia o campo culpado."""


@dataclass(frozen=True)
class Bloco:
    tipo: str
    itens: tuple[dict[str, str], ...]


# Velocidade da fala francesa. Entrada da rampa fala 15% abaixo do natural:
# calibrada pelo OUVIDO, que esta atras da leitura (ver spec, secao 2). Sobe
# por licao, no YAML, conforme o ouvido acompanha -- por isso e campo da licao
# e nao constante de codigo.
VELOCIDADE_PADRAO = "-15%"


@dataclass(frozen=True)
class Licao:
    id: str
    titulo: str
    nivel: str
    cena: tuple[str, ...]
    blocos: tuple[Bloco, ...]
    velocidade: str = VELOCIDADE_PADRAO


def carregar(caminho: str | Path) -> Licao:
    """Le o YAML, valida e devolve a Licao. Levanta LicaoInvalidaError se algo falta."""
    caminho = Path(caminho)
    bruto = yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}

    faltando = [c for c in _CAMPOS_LICAO if c not in bruto]
    if faltando:
        raise LicaoInvalidaError(f"{caminho.name}: campos ausentes: {', '.join(faltando)}")

    cena = bruto["cena"]
    if not cena:
        raise LicaoInvalidaError(
            f"{caminho.name}: campo 'cena' vazio. Sem cena nao ha arco, e o arco "
            "(mesma cena no inicio e no fim) e o unico termometro de progresso da faixa."
        )

    return Licao(
        id=str(bruto["id"]),
        titulo=str(bruto["titulo"]),
        nivel=str(bruto["nivel"]),
        cena=tuple(str(linha) for linha in cena),
        blocos=tuple(_validar_bloco(b, caminho.name, i) for i, b in enumerate(bruto["blocos"])),
        velocidade=str(bruto.get("velocidade", VELOCIDADE_PADRAO)),
    )


def _validar_bloco(bruto: dict, arquivo: str, indice: int) -> Bloco:
    tipo = bruto.get("tipo")
    if tipo not in TIPOS_VALIDOS:
        raise LicaoInvalidaError(
            f"{arquivo}: bloco {indice + 1} tem tipo '{tipo}', que nao existe. "
            f"Validos: {', '.join(TIPOS_VALIDOS)}"
        )

    itens = bruto.get("itens") or []
    obrigatorios = CAMPOS_OBRIGATORIOS[tipo]
    for j, item in enumerate(itens):
        faltando = [c for c in obrigatorios if not item.get(c)]
        if faltando:
            raise LicaoInvalidaError(
                f"{arquivo}: bloco {indice + 1} ({tipo}), item {j + 1}: "
                f"campos ausentes: {', '.join(faltando)}"
            )

    return Bloco(tipo=tipo, itens=tuple(dict(i) for i in itens))
