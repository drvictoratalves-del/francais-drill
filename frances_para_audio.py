"""Gera o MP3 de uma licao de frances.

    python scripts/frances_para_audio.py licoes/frances/01.yaml
    python scripts/frances_para_audio.py licoes/frances/01.yaml --saida "C:/tmp"

CLI separado do pacote pelo mesmo motivo de `texto_para_audio.py`: modulo
dentro de pacote com import relativo nao roda como script solto, e chamar
`python -m` exige o cwd certo. O ponto de entrada fica aqui, plano.

Spec: docs/superpowers/specs/2026-08-12-drill-frances-audio-design.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8")

from francais_drill.app import como_html  # noqa: E402
from francais_drill.escrever import como_markdown  # noqa: E402
from francais_drill.gerar import gerar  # noqa: E402
from francais_drill.licao import LicaoInvalidaError, carregar  # noqa: E402

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
    p = argparse.ArgumentParser(description="Gera o MP3 (e o PDF) de uma licao de frances.")
    p.add_argument("licao", help="caminho do YAML da licao")
    p.add_argument("--saida", default=None, help="pasta de destino (padrao: OneDrive)")
    p.add_argument("--sem-pdf", action="store_true", help="nao gerar o PDF")
    p.add_argument("--sem-app", action="store_true", help="nao gerar o app HTML")
    args = p.parse_args(argv)

    try:
        caminho = gerar(args.licao, args.saida)
    except LicaoInvalidaError as erro:
        print(f"LICAO INVALIDA: {erro}", file=sys.stderr)
        return 2

    minutos = caminho.stat().st_size * 8 / BITRATE_BPS / 60
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
