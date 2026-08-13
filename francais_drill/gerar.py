"""Sintetiza a sequencia de passos e grava o MP3.

Unica camada que toca a rede. A juncao e binaria: quadros MP3 sao
autocontidos, entao emendar bytes produz arquivo valido sem passar por ffmpeg.

Bloco que volta vazio do TTS e falha do servico, nao conteudo vazio. Sem o erro
alto, b'' entra calado na juncao e o MP3 sai com buraco que toca do inicio ao
fim sem nenhum sinal -- e num drill isso significa o aluno praticando o silencio
onde deveria estar a frase.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import edge_tts

from .licao import carregar
from .montar import Fala, Passo, Pausa, montar

_ARQ_SILENCIO = Path(__file__).parent / "assets" / "silencio_700ms.mp3"

CONCORRENCIA = 6
TENTATIVAS = 3

DESTINO_PADRAO = (
    Path.home() / "OneDrive" / "Desktop" / "Arquivos Claude" / "14 Mídia" / "Áudios de Estudo"
)


async def _sintetizar(texto: str, voz: str, velocidade: str) -> bytes:
    for _ in range(TENTATIVAS):
        fala = edge_tts.Communicate(texto, voz, rate=velocidade)
        partes = [e["data"] async for e in fala.stream() if e["type"] == "audio"]
        if partes:
            return b"".join(partes)
    raise RuntimeError(f"TTS devolveu vazio apos {TENTATIVAS} tentativas: {texto[:60]!r} ({voz})")


async def _sintetizar_todos(passos: list[Passo]) -> list[bytes]:
    silencio = _ARQ_SILENCIO.read_bytes()
    limite = asyncio.Semaphore(CONCORRENCIA)

    async def um(passo: Passo) -> bytes:
        if isinstance(passo, Pausa):
            return silencio * passo.blocos
        async with limite:
            return await _sintetizar(passo.texto, passo.voz, passo.velocidade)

    return list(await asyncio.gather(*(um(p) for p in passos)))


def gerar(caminho_licao: str | Path, destino: str | Path | None = None) -> Path:
    """Gera o MP3 da licao e devolve o caminho gravado."""
    licao = carregar(caminho_licao)
    passos = montar(licao)
    blocos = asyncio.run(_sintetizar_todos(passos))

    # T5: falha ALTA antes de gravar. MP3 com buraco e pior que MP3 ausente,
    # porque o ausente e obvio e o furado passa por pronto.
    for i, (passo, bloco) in enumerate(zip(passos, blocos, strict=True)):
        if not bloco:
            alvo = passo.texto if isinstance(passo, Fala) else f"pausa de {passo.blocos} blocos"
            raise RuntimeError(f"bloco {i + 1}/{len(passos)} saiu vazio: {alvo!r}")

    pasta = Path(destino) if destino else DESTINO_PADRAO / "Francês"
    pasta.mkdir(parents=True, exist_ok=True)
    saida = pasta / f"frances_{licao.id}_{_slug(licao.titulo)}.mp3"
    saida.write_bytes(b"".join(blocos))
    return saida


def _slug(titulo: str) -> str:
    limpo = "".join(c if c.isalnum() or c in " -" else "" for c in titulo.lower())
    return "-".join(limpo.split())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gera o MP3 de uma licao de frances.")
    p.add_argument("licao", help="caminho do YAML da licao")
    p.add_argument("--saida", default=None, help="pasta de destino (padrao: OneDrive)")
    args = p.parse_args(argv)

    caminho = gerar(args.licao, args.saida)
    duracao_s = caminho.stat().st_size * 8 / 48_000  # edge-tts entrega CBR 48 kbps
    print(f"OK: {caminho}  (~{duracao_s / 60:.1f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
