"""Carrega e valida a licao declarada em YAML.

Licao malformada falha ALTO, nomeando o campo. Nunca gerar MP3 parcial: um
audio truncado toca do inicio ao fim sem erro visivel, e o defeito so aparece
quando o aluno ja praticou em voz alta o que faltou.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

TIPOS_VALIDOS = ("decomposicao", "semaforo", "producao", "revisao")
TIPOS_LICAO = ("aula", "leitura", "drill")

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
    bloco: str = "Drills extras"
    tipo: str = "drill"
    ordem: int = 99
    foco: str = ""
    vocabulario: tuple[dict[str, str], ...] = ()
    pronuncia: tuple[dict[str, str], ...] = ()
    fala_livre: dict[str, Any] | None = None
    notion_url: str = ""


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

    tipo = str(bruto.get("tipo", "drill"))
    if tipo not in TIPOS_LICAO:
        raise LicaoInvalidaError(
            f"{caminho.name}: campo 'tipo' invalido ({tipo!r}). Use um de: {', '.join(TIPOS_LICAO)}"
        )

    vocabulario = _validar_pares(bruto.get("vocabulario"), ("fr", "pt"), caminho.name, "vocabulario")
    pronuncia = _validar_pares(bruto.get("pronuncia"), ("fr", "pt"), caminho.name, "pronuncia")
    fala_livre = _validar_fala_livre(bruto.get("fala_livre"), caminho.name)

    return Licao(
        id=str(bruto["id"]),
        titulo=str(bruto["titulo"]),
        nivel=str(bruto["nivel"]),
        cena=tuple(str(linha) for linha in cena),
        blocos=tuple(_validar_bloco(b, caminho.name, i) for i, b in enumerate(bruto["blocos"])),
        velocidade=str(bruto.get("velocidade", VELOCIDADE_PADRAO)),
        bloco=str(bruto.get("bloco", "Drills extras")),
        tipo=tipo,
        ordem=int(bruto.get("ordem", 99)),
        foco=str(bruto.get("foco", "")),
        vocabulario=vocabulario,
        pronuncia=pronuncia,
        fala_livre=fala_livre,
        notion_url=str(bruto.get("notion_url", "")),
    )


def _validar_bloco(bruto: dict, arquivo: str, indice: int) -> Bloco:
    tipo = bruto.get("tipo")
    if tipo not in TIPOS_VALIDOS:
        raise LicaoInvalidaError(
            f"{arquivo}: bloco {indice + 1} tem tipo invalido ({tipo!r}). "
            f"Use um de: {', '.join(TIPOS_VALIDOS)}"
        )

    itens = bruto.get("itens")
    if itens is None:
        raise LicaoInvalidaError(f"{arquivo}: bloco {indice + 1} ({tipo}) sem campo 'itens'")

    obrigatorios = CAMPOS_OBRIGATORIOS[tipo]
    for j, item in enumerate(itens):
        faltando = [c for c in obrigatorios if not item.get(c)]
        if faltando:
            raise LicaoInvalidaError(
                f"{arquivo}: bloco {indice + 1} ({tipo}), item {j + 1}: "
                f"campos ausentes: {', '.join(faltando)}"
            )

    return Bloco(tipo=tipo, itens=tuple({k: str(v) for k, v in item.items()} for item in itens))


def _validar_pares(
    bruto: Any,
    obrigatorios: tuple[str, ...],
    arquivo: str,
    campo: str,
) -> tuple[dict[str, str], ...]:
    if not bruto:
        return ()
    if not isinstance(bruto, list):
        raise LicaoInvalidaError(f"{arquivo}: campo '{campo}' deve ser uma lista")
    saida: list[dict[str, str]] = []
    for j, item in enumerate(bruto):
        if not isinstance(item, dict):
            raise LicaoInvalidaError(f"{arquivo}: {campo}[{j + 1}] deve ser um objeto")
        faltando = [c for c in obrigatorios if not item.get(c)]
        if faltando:
            raise LicaoInvalidaError(
                f"{arquivo}: {campo}[{j + 1}]: campos ausentes: {', '.join(faltando)}"
            )
        saida.append({k: str(v) for k, v in item.items()})
    return tuple(saida)


def _validar_fala_livre(bruto: Any, arquivo: str) -> dict[str, Any] | None:
    if not bruto:
        return None
    if not isinstance(bruto, dict):
        raise LicaoInvalidaError(f"{arquivo}: campo 'fala_livre' deve ser um objeto")
    if not bruto.get("enunciado"):
        raise LicaoInvalidaError(f"{arquivo}: campo 'fala_livre' exige 'enunciado'")
    passos = bruto.get("passos") or []
    if not isinstance(passos, list):
        raise LicaoInvalidaError(f"{arquivo}: 'fala_livre.passos' deve ser uma lista")
    return {
        "enunciado": str(bruto["enunciado"]),
        "passos": [str(p) for p in passos],
        "criterio": str(bruto.get("criterio", "")),
        "duracao_alvo_s": int(bruto.get("duracao_alvo_s", 60)),
    }
