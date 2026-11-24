"""Sintetiza a sequencia de passos e grava os MP3s (caminhada e web).

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
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

import edge_tts

from .licao import Licao, carregar
from .montar import VOZ_FR, Fala, Passo, Pausa, lento, montar, montar_bloco

_ARQ_SILENCIO = Path(__file__).parent / "assets" / "silencio_700ms.mp3"

CONCORRENCIA = 6
TENTATIVAS = 3
BITRATE_BPS = 48_000  # edge-tts entrega CBR 48 kbps

DESTINO_PADRAO = (
    Path.home() / "OneDrive" / "Desktop" / "Arquivos Claude" / "14 Mídia" / "Áudios de Estudo"
)

# Tabelas MPEG Layer III para medir duracao exata de quadros MP3 sem ffmpeg.
_BITRATES_V1_L3 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0)
_BITRATES_V2_L3 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0)
_SAMPLERATES = {
    3: (44100, 48000, 32000),  # MPEG 1
    2: (22050, 24000, 16000),  # MPEG 2
    0: (11025, 12000, 8000),  # MPEG 2.5
}


def duracao_mp3(dados: bytes) -> float:
    """Calcula a duracao real (em segundos) percorrendo cabecalhos MPEG Layer III."""
    n = len(dados)
    if not n:
        return 0.0

    pos = 0
    # Pula cabecalho ID3v2 se houver.
    if n >= 10 and dados[:3] == b"ID3":
        tam = (
            ((dados[6] & 0x7F) << 21)
            | ((dados[7] & 0x7F) << 14)
            | ((dados[8] & 0x7F) << 7)
            | (dados[9] & 0x7F)
        )
        pos = 10 + tam

    total_s = 0.0
    quadros = 0
    while pos + 4 <= n:
        if dados[pos] != 0xFF or (dados[pos + 1] & 0xE0) != 0xE0:
            pos += 1
            continue
        ver = (dados[pos + 1] >> 3) & 0x03
        layer = (dados[pos + 1] >> 1) & 0x03
        br_idx = (dados[pos + 2] >> 4) & 0x0F
        sr_idx = (dados[pos + 2] >> 2) & 0x03
        pad = (dados[pos + 2] >> 1) & 0x01

        if ver == 1 or layer != 1 or br_idx in (0, 15) or sr_idx == 3:
            pos += 1
            continue

        sr = _SAMPLERATES[ver][sr_idx]
        if ver == 3:
            br = _BITRATES_V1_L3[br_idx] * 1000
            amostras = 1152
            tam_quadro = (144 * br) // sr + pad
        else:
            br = _BITRATES_V2_L3[br_idx] * 1000
            amostras = 576
            tam_quadro = (72 * br) // sr + pad

        if tam_quadro < 4 or pos + tam_quadro > n:
            break

        total_s += amostras / sr
        quadros += 1
        pos += tam_quadro

    if quadros == 0:
        return n * 8 / BITRATE_BPS
    return total_s


async def _sintetizar(texto: str, voz: str, velocidade: str) -> bytes:
    for tentativa in range(TENTATIVAS):
        try:
            fala = edge_tts.Communicate(texto, voz, rate=velocidade)
            partes = [e["data"] async for e in fala.stream() if e["type"] == "audio"]
            if partes:
                return b"".join(partes)
        except Exception:
            if tentativa + 1 >= TENTATIVAS:
                raise
            await asyncio.sleep(0.8 * (tentativa + 1))
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


def _validar_blocos_nao_vazios(passos: list[Passo], blocos: list[bytes]) -> None:
    # T5: falha ALTA antes de gravar. MP3 com buraco e pior que MP3 ausente,
    # porque o ausente e obvio e o furado passa por pronto.
    for i, (passo, bloco) in enumerate(zip(passos, blocos, strict=True)):
        if not bloco:
            alvo = passo.texto if isinstance(passo, Fala) else f"pausa de {passo.blocos} blocos"
            raise RuntimeError(f"bloco {i + 1}/{len(passos)} saiu vazio: {alvo!r}")


def gerar(caminho_licao: str | Path, destino: str | Path | None = None) -> Path:
    """Gera o MP3 de caminhada da licao e devolve o caminho gravado."""
    licao = carregar(caminho_licao)
    passos = montar(licao)
    blocos = asyncio.run(_sintetizar_todos(passos))
    _validar_blocos_nao_vazios(passos, blocos)

    pasta = Path(destino) if destino else DESTINO_PADRAO / "Francês"
    pasta.mkdir(parents=True, exist_ok=True)
    saida = pasta / f"frances_{licao.id}_{_slug(licao.titulo)}.mp3"
    saida.write_bytes(b"".join(blocos))
    return saida


def compilar_bloco(
    caminhos_licoes: list[str | Path],
    nome_bloco: str,
    destino: str | Path | None = None,
) -> Path:
    """Compila varias licoes em um unico MP3 longo continuo de caminhada."""
    licoes = [carregar(c) for c in caminhos_licoes]
    passos = montar_bloco(licoes)
    blocos = asyncio.run(_sintetizar_todos(passos))
    _validar_blocos_nao_vazios(passos, blocos)

    pasta = Path(destino) if destino else DESTINO_PADRAO / "Francês"
    pasta.mkdir(parents=True, exist_ok=True)
    saida = pasta / f"bloco_{_slug(nome_bloco)}.mp3"
    saida.write_bytes(b"".join(blocos))
    return saida


def _falas_pronuncia_web(licao: Licao) -> list[dict[str, str]]:
    """Lista padronizada de falas do Estagio 2 (Pronuncia / Shadowing)."""
    if licao.pronuncia:
        return [dict(item) for item in licao.pronuncia]
    itens: list[dict[str, str]] = []
    vistos: set[str] = set()
    for bloco in licao.blocos:
        if bloco.tipo == "decomposicao":
            for item in bloco.itens:
                if item["fr"] not in vistos:
                    vistos.add(item["fr"])
                    itens.append({"fr": item["fr"], "pt": item["pt"]})
    for linha in licao.cena:
        if linha not in vistos:
            vistos.add(linha)
            itens.append({"fr": linha, "pt": ""})
    return itens


def _itens_drill_web(licao: Licao) -> list[dict[str, str]]:
    """Lista de itens cobrados no Estagio 3 (Drill: producao + semaforo)."""
    itens: list[dict[str, str]] = []
    for bloco in licao.blocos:
        if bloco.tipo == "producao":
            for item in bloco.itens:
                itens.append(
                    {
                        "tipo": "producao",
                        "pergunta": item["pergunta"],
                        "resposta": item["resposta"],
                    }
                )
        elif bloco.tipo == "semaforo":
            for item in bloco.itens:
                itens.append(
                    {
                        "tipo": "semaforo",
                        "pergunta": f"Comment dit-on, correctement : « {item['errado']} » ?",
                        "errado": item["errado"],
                        "resposta": item["certo"],
                        "nota": item.get("nota_pt", ""),
                    }
                )
    return itens


def _pedidos_clips_treino(licao: Licao) -> list[tuple[str, str]]:
    """Devolve pares unicos (velocidade, texto_fr) necessarios para o sprite de treino."""
    vel = licao.velocidade
    devagar = lento(vel)
    pedidos: list[tuple[str, str]] = []
    vistos: set[tuple[str, str]] = set()

    def adicionar(v: str, texto: str) -> None:
        chave = (v, texto)
        if texto and chave not in vistos:
            vistos.add(chave)
            pedidos.append(chave)

    for item in _falas_pronuncia_web(licao):
        adicionar(vel, item["fr"])
        adicionar(devagar, item["fr"])

    for item in _itens_drill_web(licao):
        adicionar(vel, item["pergunta"])
        adicionar(vel, item["resposta"])
        adicionar(devagar, item["resposta"])

    return pedidos


def _hash_conteudo_web(licao: Licao) -> str:
    payload = {
        "velocidade": licao.velocidade,
        "cena": list(licao.cena),
        "clips": _pedidos_clips_treino(licao),
        "versao": 2,
    }
    bruto = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(bruto).hexdigest()[:16]


def gerar_midia_web(
    licao: Licao,
    pasta_audio: Path,
    slug_base: str,
    pasta_cache: Path | None = None,
    forcar: bool = False,
) -> dict:
    """Gera o MP3 longo da cena (com timestamps por fala) + sprite de treino para o app web."""
    pasta_audio.mkdir(parents=True, exist_ok=True)
    arq_cena = pasta_audio / f"{slug_base}_cena.mp3"
    arq_treino = pasta_audio / f"{slug_base}_treino.mp3"

    assinatura = _hash_conteudo_web(licao)
    arq_cache = (pasta_cache / f"{slug_base}.json") if pasta_cache else None
    if (
        not forcar
        and arq_cache
        and arq_cache.exists()
        and arq_cena.exists()
        and arq_treino.exists()
    ):
        salvo = json.loads(arq_cache.read_text(encoding="utf-8-sig"))
        if salvo.get("hash") == assinatura:
            return salvo["midia"]

    silencio = _ARQ_SILENCIO.read_bytes()
    dur_silencio = duracao_mp3(silencio)
    vel = licao.velocidade

    # 1. Sintetiza cena linha por linha + todos os clipes de treino num unico asyncio.run
    pedidos_treino = _pedidos_clips_treino(licao)
    passos_cena = [Fala(linha, VOZ_FR, vel) for linha in licao.cena]
    passos_treino = [Fala(texto, VOZ_FR, v) for v, texto in pedidos_treino]

    todos_passos: list[Passo] = [*passos_cena, *passos_treino]
    todos_bytes = asyncio.run(_sintetizar_todos(todos_passos))
    _validar_blocos_nao_vazios(todos_passos, todos_bytes)

    n_cena = len(passos_cena)
    bytes_cena = todos_bytes[:n_cena]
    bytes_treino = todos_bytes[n_cena:]

    # Monta cena MP3 com pausa curta entre falas e timestamps exatos
    partes_cena: list[bytes] = []
    cena_tempos: list[list[float]] = []
    cursor = 0.0
    for idx, chunk in enumerate(bytes_cena):
        if idx > 0:
            partes_cena.append(silencio)
            cursor += dur_silencio
        dur = duracao_mp3(chunk)
        cena_tempos.append([round(cursor, 3), round(cursor + dur, 3)])
        partes_cena.append(chunk)
        cursor += dur
    arq_cena.write_bytes(b"".join(partes_cena))
    cena_duracao = round(cursor, 2)

    # Monta sprite de treino MP3 (1 silencio de guarda entre clipes para corte limpo)
    partes_treino: list[bytes] = []
    clips: dict[str, list[float]] = {}
    cursor_t = 0.0
    for (v, texto), chunk in zip(pedidos_treino, bytes_treino, strict=True):
        dur = duracao_mp3(chunk)
        chave = f"{v}|{texto}"
        clips[chave] = [round(cursor_t, 3), round(cursor_t + dur, 3)]
        partes_treino.append(chunk)
        cursor_t += dur
        partes_treino.append(silencio)
        cursor_t += dur_silencio
    arq_treino.write_bytes(b"".join(partes_treino))

    midia = {
        "cena_src": f"./audio/{arq_cena.name}",
        "cena_duracao": cena_duracao,
        "cena_tempos": cena_tempos,
        "treino_src": f"./audio/{arq_treino.name}",
        "clips": clips,
        "vel_normal": vel,
        "vel_lento": lento(vel),
    }

    if arq_cache:
        arq_cache.parent.mkdir(parents=True, exist_ok=True)
        arq_cache.write_text(
            json.dumps({"hash": assinatura, "midia": midia}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return midia


def _slug(titulo: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", titulo) if not unicodedata.combining(c)
    )
    limpo = "".join(c if c.isalnum() or c in " -" else "" for c in sem_acento.lower())
    return "-".join(limpo.split())


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gera o MP3 de uma licao de frances.")
    p.add_argument("licao", help="caminho do YAML da licao")
    p.add_argument("--saida", default=None, help="pasta de destino (padrao: OneDrive)")
    args = p.parse_args(argv)

    caminho = gerar(args.licao, args.saida)
    duracao_s = duracao_mp3(caminho.read_bytes())
    print(f"OK: {caminho}  (~{duracao_s / 60:.1f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
