"""Constroi o site estatico completo (docs/) a partir dos YAMLs em licoes/frances/.

Elimina a manutencao manual de docs/index.html, gera os MP3s web sincronizados
em docs/audio/ e inclui manifest + service worker leve para uso no celular.
"""

from __future__ import annotations

import html as html_lib
import json
from collections import OrderedDict
from pathlib import Path

from .app import como_html
from .gerar import _slug, gerar_midia_web
from .licao import Licao, carregar


def slug_arquivo(licao: Licao) -> str:
    """Preserva os nomes legados (frances_01_...) e padroniza as novas aulas sem repetir o prefixo."""
    base = _slug(licao.titulo)
    if licao.id.isdigit():
        return f"frances_{licao.id}_{base}"
    pref = _slug(licao.id)
    if base.startswith(pref + "-"):
        base = base[len(pref) + 1 :]
    return f"{pref}_{base}"


def _formatar_duracao(segundos: float) -> str:
    if not segundos:
        return ""
    total = int(round(segundos))
    m, s = divmod(total, 60)
    return f"{m} min {s:02d} s" if m else f"{s} s"


def gerar_indice_html(licoes_info: list[dict]) -> str:
    """Gera docs/index.html agrupado por bloco com progresso e Caderno de Erros."""
    grupos: OrderedDict[str, list[dict]] = OrderedDict()
    for info in licoes_info:
        grupos.setdefault(info["bloco"], []).append(info)

    blocos_html: list[str] = []
    for bloco, itens in grupos.items():
        cards: list[str] = []
        for it in itens:
            dur = _formatar_duracao(it.get("duracao_s", 0))
            meta_partes = [it["id"].upper(), it["nivel"]]
            if dur:
                meta_partes.append(f"🎧 {dur}")
            meta = " · ".join(meta_partes)
            foco_html = (
                f'<div class="foco">{html_lib.escape(it["foco"])}</div>' if it.get("foco") else ""
            )
            cards.append(
                f'    <a class="licao" href="./{html_lib.escape(it["arquivo"])}" '
                f'data-id="{html_lib.escape(it["id"])}">\n'
                f'      <div class="n"><span>{html_lib.escape(meta)}</span>'
                f'<span class="selo-prog"></span></div>\n'
                f'      <div class="t">{html_lib.escape(it["titulo"])}</div>\n'
                f'      {foco_html}\n'
                f"    </a>"
            )
        blocos_html.append(
            f'  <section class="grupo">\n'
            f'    <h2>{html_lib.escape(bloco)}</h2>\n'
            + "\n".join(cards)
            + "\n  </section>"
        )

    return _INDEX_TEMPLATE.replace("__BLOCOS__", "\n\n".join(blocos_html))


def construir_site(
    pasta_licoes: Path,
    pasta_docs: Path,
    forcar_audio: bool = False,
    pasta_cache: Path | None = None,
) -> list[dict]:
    """Compila todos os YAMLs de `pasta_licoes` para `pasta_docs` (HTML + audio + index + PWA)."""
    caminhos = sorted(pasta_licoes.glob("*.yaml"))
    licoes = sorted((carregar(c) for c in caminhos), key=lambda l: (l.ordem, l.id))

    pasta_docs.mkdir(parents=True, exist_ok=True)
    pasta_audio = pasta_docs / "audio"
    cache_dir = pasta_cache if pasta_cache is not None else pasta_docs.parent / ".audio_cache"

    licoes_info: list[dict] = []
    for licao in licoes:
        stem = slug_arquivo(licao)
        midia = gerar_midia_web(
            licao,
            pasta_audio=pasta_audio,
            slug_base=stem,
            pasta_cache=cache_dir,
            forcar=forcar_audio,
        )
        arq_html = f"{stem}.html"
        (pasta_docs / arq_html).write_text(como_html(licao, midia=midia), encoding="utf-8")
        licoes_info.append(
            {
                "id": licao.id,
                "titulo": licao.titulo,
                "nivel": licao.nivel,
                "bloco": licao.bloco,
                "tipo": licao.tipo,
                "ordem": licao.ordem,
                "foco": licao.foco,
                "arquivo": arq_html,
                "duracao_s": midia.get("cena_duracao", 0),
            }
        )

    (pasta_docs / "index.html").write_text(gerar_indice_html(licoes_info), encoding="utf-8")
    (pasta_docs / "manifest.webmanifest").write_text(_MANIFEST, encoding="utf-8")
    (pasta_docs / "sw.js").write_text(_SERVICE_WORKER, encoding="utf-8")
    return licoes_info


_MANIFEST = json.dumps(
    {
        "name": "Drill de français",
        "short_name": "Français Drill",
        "description": "Áudios longos sincronizados, falas para pronunciar (A/B + IA) e drill ativo de francês.",
        "start_url": "./index.html",
        "display": "standalone",
        "background_color": "#12100e",
        "theme_color": "#12100e",
        "lang": "fr",
    },
    ensure_ascii=False,
    indent=2,
)

_SERVICE_WORKER = """const CACHE = "francais-drill-v2";

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(["./", "./index.html"])));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // Audio MP3: cache-first depois de ouvido (ideal para caminhar offline).
  if (url.pathname.endsWith(".mp3")) {
    event.respondWith(
      caches.open(CACHE).then((cache) =>
        cache.match(req).then((hit) => hit || fetch(req).then((res) => {
          if (res.ok && res.status === 200) cache.put(req, res.clone());
          return res;
        }))
      )
    );
    return;
  }

  // HTML/assets: network-first com fallback para cache.
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && res.status === 200) {
          const clone = res.clone();
          caches.open(CACHE).then((c) => c.put(req, clone));
        }
        return res;
      })
      .catch(() => caches.match(req))
  );
});
"""

_INDEX_TEMPLATE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#12100e">
<link rel="manifest" href="./manifest.webmanifest">
<title>Drill de français</title>
<style>
  :root {
    --fundo: #12100e; --superficie: #1b1815; --borda: rgba(245,241,234,.14);
    --borda-forte: rgba(245,241,234,.36); --tinta: #f5f1ea; --suave: #a3998e;
    --acento: #d8a974; --verde: #7ee2ab;
    --serif: "Georgia","Iowan Old Style",serif;
    --sans: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100svh; background: var(--fundo); color: var(--tinta);
    font-family: var(--sans); padding: 1.8rem 1.15rem 3.5rem;
    max-width: 44rem; margin-inline: auto; line-height: 1.5;
  }
  header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.6rem; }
  h1 { font-family: var(--serif); font-size: 1.75rem; font-weight: 400; margin: 0 0 .3rem; }
  p.sub { color: var(--suave); margin: 0; font-size: .92rem; }
  .btn {
    background: var(--superficie); color: var(--tinta); border: 1px solid var(--borda);
    border-radius: 8px; padding: .45rem .8rem; font-size: .82rem; cursor: pointer; min-height: 38px;
  }
  .btn:hover { border-color: var(--borda-forte); }
  .btn.ativo { border-color: var(--acento); color: var(--acento); }
  .grupo { margin-top: 1.75rem; }
  .grupo h2 {
    font-size: .78rem; letter-spacing: .1em; text-transform: uppercase;
    color: var(--acento); margin: 0 0 .75rem; font-weight: 600;
  }
  a.licao {
    display: block; text-decoration: none; color: var(--tinta);
    background: var(--superficie); border: 1px solid var(--borda);
    border-radius: 10px; padding: .95rem 1.05rem; margin-bottom: .65rem;
    transition: border-color 140ms ease;
  }
  a.licao:hover { border-color: var(--borda-forte); }
  .n {
    display: flex; justify-content: space-between; align-items: center; gap: .5rem;
    color: var(--suave); font-size: .75rem; letter-spacing: .07em;
  }
  .selo-prog { color: var(--verde); font-weight: 600; letter-spacing: 0; }
  .t { font-family: var(--serif); font-size: 1.14rem; margin-top: .22rem; }
  .foco { color: var(--suave); font-size: .84rem; margin-top: .25rem; }

  .caderno {
    margin-top: 2rem; background: var(--superficie); border: 1px solid var(--borda);
    border-radius: 12px; padding: 1.1rem;
  }
  .erro-item {
    display: flex; justify-content: space-between; align-items: flex-start; gap: .75rem;
    padding: .65rem 0; border-top: 1px solid var(--borda);
  }
  .erro-item:first-of-type { border-top: none; }
  .erro-fr { font-family: var(--serif); font-size: 1rem; }
  .erro-meta { font-size: .8rem; color: var(--suave); margin-top: .15rem; }

  footer { color: var(--suave); font-size: .8rem; margin-top: 2.2rem; line-height: 1.55; }
  dialog {
    background: var(--superficie); color: var(--tinta);
    border: 1px solid var(--borda-forte); border-radius: 14px;
    padding: 1.25rem; max-width: 28rem; width: calc(100% - 2rem); margin: auto;
  }
  dialog::backdrop { background: rgba(0,0,0,.72); }
  .campo { display: flex; flex-direction: column; gap: .35rem; margin-top: .85rem; }
  .campo label { font-size: .82rem; color: var(--suave); }
  .campo input {
    background: var(--fundo); color: var(--tinta);
    border: 1px solid var(--borda-forte); border-radius: 8px;
    padding: .65rem .75rem; font-size: .92rem;
  }
  .acoes { display: flex; gap: .5rem; margin-top: 1rem; }
</style>
</head>
<body>
  <header>
    <div>
      <h1>Drill de français</h1>
      <p class="sub">Áudio longo narrado, falas para pronunciar (A/B + IA) e resposta em voz alta.</p>
    </div>
    <button class="btn" id="btn-ia" type="button">⚙️ IA</button>
  </header>

__BLOCOS__

  <section class="caderno" id="sec-erros">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem">
      <h2 style="margin:0;font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;color:var(--acento)">
        🔁 Caderno de Erros (local)
      </h2>
      <span id="erros-count" style="font-size:.78rem;color:var(--suave)"></span>
    </div>
    <div id="erros-lista"></div>
  </section>

  <footer>
    O verde no Drill diz que as palavras certas saíram — não comprova pronúncia.
    Para treinar som, ritmo e sotaque, use <b>Gravar + Comparar A/B</b> ou a avaliação por áudio (IA) em cada lição.
  </footer>

  <dialog id="modal-ia">
    <h3 style="font-family:var(--serif);font-weight:400;margin:0 0 .4rem">Avaliação de pronúncia com IA</h3>
    <p style="font-size:.82rem;color:var(--suave);margin:0">
      Chave Gemini salva apenas no <code>localStorage</code> deste navegador (<code>store: false</code>).
    </p>
    <div class="campo">
      <label for="ia-key">Gemini API Key</label>
      <input type="password" id="ia-key" placeholder="AIza..." autocomplete="off">
    </div>
    <div class="campo">
      <label for="ia-model">Modelo</label>
      <input type="text" id="ia-model" value="gemini-3.8-flash">
    </div>
    <div class="acoes">
      <button class="btn" style="flex:1;background:var(--tinta);color:var(--fundo);font-weight:600" id="ia-salvar" type="button">Salvar</button>
      <button class="btn" id="ia-limpar" type="button">Remover</button>
      <button class="btn" id="ia-fechar" type="button">Fechar</button>
    </div>
  </dialog>

<script>
const STORAGE_PROG = "francais_drill_progresso_v1";
const STORAGE_ERROS = "francais_drill_erros_v1";
const STORAGE_KEY = "francais_drill_gemini_key";
const STORAGE_MODEL = "francais_drill_gemini_model";

function ler(k, fb) { try { return JSON.parse(localStorage.getItem(k) || "null") ?? fb; } catch { return fb; } }

const prog = ler(STORAGE_PROG, {});
document.querySelectorAll("a.licao").forEach((a) => {
  const info = prog[a.dataset.id];
  if (info) a.querySelector(".selo-prog").textContent = "✓ " + info.sessoes + "×";
});

function renderErros() {
  const lista = ler(STORAGE_ERROS, []);
  document.getElementById("erros-count").textContent = lista.length ? lista.length + " itens" : "Vazio";
  const box = document.getElementById("erros-lista");
  box.innerHTML = "";
  if (!lista.length) {
    box.innerHTML = '<p style="font-size:.84rem;color:var(--suave);margin:.3rem 0 0">As frases marcadas ou erradas nos drills aparecem aqui para revisão.</p>';
    return;
  }
  lista.forEach((e) => {
    const row = document.createElement("div");
    row.className = "erro-item";
    row.innerHTML = '<div><div class="erro-fr"></div><div class="erro-meta"></div></div>' +
      '<button class="btn" type="button">Dominada ✓</button>';
    row.querySelector(".erro-fr").textContent = e.fr;
    row.querySelector(".erro-meta").textContent = [e.origem, e.nota, e.data].filter(Boolean).join(" · ");
    row.querySelector("button").addEventListener("click", () => {
      const nova = ler(STORAGE_ERROS, []).filter((x) => x.fr !== e.fr);
      localStorage.setItem(STORAGE_ERROS, JSON.stringify(nova));
      renderErros();
    });
    box.appendChild(row);
  });
}
renderErros();

function atualizarIA() {
  const tem = Boolean((localStorage.getItem(STORAGE_KEY) || "").trim());
  const b = document.getElementById("btn-ia");
  b.classList.toggle("ativo", tem);
  b.textContent = tem ? "✨ IA ativa" : "⚙️ IA";
}
atualizarIA();
document.getElementById("btn-ia").addEventListener("click", () => {
  document.getElementById("ia-key").value = localStorage.getItem(STORAGE_KEY) || "";
  document.getElementById("ia-model").value = localStorage.getItem(STORAGE_MODEL) || "gemini-3.8-flash";
  document.getElementById("modal-ia").showModal();
});
document.getElementById("ia-salvar").addEventListener("click", () => {
  localStorage.setItem(STORAGE_KEY, document.getElementById("ia-key").value.trim());
  localStorage.setItem(STORAGE_MODEL, document.getElementById("ia-model").value.trim() || "gemini-3.8-flash");
  atualizarIA();
  document.getElementById("modal-ia").close();
});
document.getElementById("ia-limpar").addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY);
  atualizarIA();
  document.getElementById("modal-ia").close();
});
document.getElementById("ia-fechar").addEventListener("click", () => document.getElementById("modal-ia").close());

if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  navigator.serviceWorker.register("./sw.js").catch(() => {});
}
</script>
</body>
</html>
"""
