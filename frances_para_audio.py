"""Gera MP3 de caminhada, blocos longos e o site web completo do francais-drill.

    python frances_para_audio.py licoes/frances/01.yaml
    python frances_para_audio.py licoes/frances/01.yaml --saida ./saida --sem-pdf
    python frances_para_audio.py --construir-site docs
    python frances_para_audio.py --compilar-bloco licoes/frances/aula_0*.yaml --nome bloco-1 --saida ./saida

CLI separado do pacote para rodar direto sem `python -m`.
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

from francais_drill.app import como_html  # noqa: E402
from francais_drill.escrever import como_markdown  # noqa: E402
from francais_drill.gerar import compilar_bloco, duracao_mp3, gerar  # noqa: E402
from francais_drill.licao import LicaoInvalidaError, carregar  # noqa: E402
from francais_drill.site import construir_site  # noqa: E402

BITRATE_BPS = 48_000  # edge-tts entrega CBR 48 kbps

# Fonte com cobertura de acento frances (circunflexo, trema, cedilha) presente
# no Windows por padrao. Sem isso o xelatex engole o caractere em silencio.
FONTE_PDF = "Georgia"


def _gerar_pdf(caminho_licao: Path, pasta: Path, nome: str) -> Path | None:
    """Converte a licao em PDF via pandoc. Devolve None se o pandoc faltar."""
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("pandoc"):
        return None

    md = como_markdown(carregar(caminho_licao))
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(md)
        origem = Path(tmp.name)

    destino = pasta / f"{nome}.pdf"
    try:
        subprocess.run(
            [
                "pandoc",
                str(origem),
                "-o",
                str(destino),
                "--pdf-engine=xelatex",
                "-V",
                "geometry:margin=2.2cm",
                "-V",
                f"mainfont={FONTE_PDF}",
                "-V",
                "fontsize=12pt",
                "-V",
                "linkcolor=black",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        origem.unlink(missing_ok=True)
    return destino


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gera MP3 de caminhada, bloco longo ou o site web.")
    p.add_argument("licao", nargs="?", help="caminho do YAML da licao")
    p.add_argument("--saida", default=None, help="pasta de destino (padrao: OneDrive)")
    p.add_argument("--sem-pdf", action="store_true", help="nao gerar o PDF")
    p.add_argument("--sem-app", action="store_true", help="nao gerar o app HTML")
    p.add_argument(
        "--construir-site",
        metavar="PASTA_DOCS",
        default=None,
        help="gera HTML + audio web + index.html para todos os YAMLs",
    )
    p.add_argument(
        "--pasta-licoes",
        default="licoes/frances",
        help="pasta de YAMLs usada por --construir-site (padrao: licoes/frances)",
    )
    p.add_argument(
        "--forcar-audio",
        action="store_true",
        help="regera todos os MP3s web ignorando o cache",
    )
    p.add_argument(
        "--compilar-bloco",
        nargs="+",
        metavar="YAML_OU_GLOB",
        default=None,
        help="compila varias licoes em um unico MP3 longo de caminhada",
    )
    p.add_argument(
        "--nome",
        default="bloco",
        help="nome do arquivo de saida para --compilar-bloco",
    )
    args = p.parse_args(argv)

    if args.construir_site:
        try:
            itens = construir_site(
                pasta_licoes=Path(args.pasta_licoes),
                pasta_docs=Path(args.construir_site),
                forcar_audio=args.forcar_audio,
            )
        except LicaoInvalidaError as erro:
            print(f"LICAO INVALIDA: {erro}", file=sys.stderr)
            return 2
        print(f"OK: site construido em {args.construir_site} ({len(itens)} licoes)")
        for it in itens:
            print(f"  - {it['arquivo']} ({it['duracao_s']:.0f}s)")
        return 0

    if args.compilar_bloco:
        caminhos: list[Path] = []
        for padrao in args.compilar_bloco:
            achados = sorted(glob.glob(padrao))
            caminhos.extend(Path(a) for a in (achados or [padrao]))
        try:
            caminho = compilar_bloco(caminhos, args.nome, args.saida)
        except (LicaoInvalidaError, ValueError) as erro:
            print(f"ERRO: {erro}", file=sys.stderr)
            return 2
        minutos = duracao_mp3(caminho.read_bytes()) / 60
        print(f"OK: {caminho}")
        print(f"    {caminho.stat().st_size:,} bytes  (~{minutos:.1f} min, {len(caminhos)} licoes)")
        return 0

    if not args.licao:
        p.error("informe o caminho de uma licao YAML, --construir-site ou --compilar-bloco")

    try:
        caminho = gerar(args.licao, args.saida)
    except LicaoInvalidaError as erro:
        print(f"LICAO INVALIDA: {erro}", file=sys.stderr)
        return 2

    minutos = duracao_mp3(caminho.read_bytes()) / 60
    print(f"OK: {caminho}")
    print(f"    {caminho.stat().st_size:,} bytes  (~{minutos:.1f} min)")

    if not args.sem_pdf:
        pdf = _gerar_pdf(Path(args.licao), caminho.parent, caminho.stem)
        if pdf is None:
            print("AVISO: pandoc nao encontrado; PDF nao gerado.", file=sys.stderr)
        else:
            print(f"OK: {pdf}")

    if not args.sem_app:
        app = caminho.parent / f"{caminho.stem}.html"
        app.write_text(como_html(carregar(args.licao)), encoding="utf-8")
        print(f"OK: {app}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
