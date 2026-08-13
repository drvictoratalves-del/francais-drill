"""Gera o app da licao: HTML autocontido, com semaforo e microfone.

MESMA fonte de dados do MP3 e do PDF -- o YAML da licao. Tres saidas, uma
verdade. Se o app dissesse coisa diferente do audio, o aluno praticaria duas
licoes distintas achando que e uma.

O app e o Praktika sem o avatar: ele pergunta em frances, ouve a resposta pelo
microfone, e pisca a tela inteira de verde ou vermelho. O rosto animado ficou
de fora por decisao registrada no spec -- e a parte cara e a que menos ensina.

LIMITE CONHECIDO E NAO MEDIDO: a Web Speech API (reconhecimento) e solida no
Chrome desktop e INCERTA no Safari do iPhone. O app detecta a ausencia e cai
para um modo sem microfone, em que o proprio aluno declara se acertou. Cair
para autoavaliacao e pior pedagogicamente, mas e honesto -- melhor que uma tela
que nao responde e nao diz por que.
"""

from __future__ import annotations

import json

from .licao import Licao

# CSS e JS vivem aqui como texto porque o app e UM arquivo por desenho: ele vai
# para o OneDrive e abre por duplo clique, sem servidor, sem build, sem rede.
_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>__TITULO__</title>
<style>
  :root {
    --fundo: #12100e;
    --tinta: #f5f1ea;
    --suave: #8a8178;
    --verde: #1f7a4d;
    --vermelho: #8c2f2f;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
  body {
    background: var(--fundo); color: var(--tinta);
    font-family: "Georgia", "Iowan Old Style", serif;
    min-height: 100svh; display: flex; flex-direction: column;
    transition: background 260ms ease;
  }
  body.acerto { background: var(--verde); }
  body.erro   { background: var(--vermelho); }

  header {
    padding: 1.4rem 1.5rem 0; display: flex; justify-content: space-between;
    align-items: baseline; font-size: .78rem; letter-spacing: .09em;
    text-transform: uppercase; color: var(--suave);
  }
  body.acerto header, body.erro header { color: rgba(255,255,255,.75); }

  main {
    flex: 1; display: flex; flex-direction: column; justify-content: center;
    gap: 1.6rem; padding: 2rem 1.6rem; max-width: 40rem; margin: 0 auto; width: 100%;
  }
  .rotulo { font-size: .74rem; letter-spacing: .12em; text-transform: uppercase; color: var(--suave); }
  body.acerto .rotulo, body.erro .rotulo { color: rgba(255,255,255,.8); }

  .frase { font-size: clamp(1.65rem, 5.5vw, 2.7rem); line-height: 1.25; }
  .traducao { font-size: 1rem; color: var(--suave); font-style: italic; }
  body.acerto .traducao, body.erro .traducao { color: rgba(255,255,255,.85); }

  .ouvido { font-size: 1.05rem; color: var(--suave); min-height: 1.5em; }
  .ouvido b { color: var(--tinta); font-weight: normal; }

  .certo { font-size: clamp(1.3rem, 4vw, 1.9rem); line-height: 1.3; }
  .nota { font-size: .95rem; line-height: 1.5; opacity: .9; }

  footer { padding: 1.2rem 1.6rem 2.2rem; display: flex; gap: .8rem;
           max-width: 40rem; margin: 0 auto; width: 100%; }
  button {
    flex: 1; padding: 1.05rem 1rem; font-size: 1rem; font-family: inherit;
    border: 1px solid currentColor; background: transparent; color: inherit;
    border-radius: 2px; cursor: pointer; letter-spacing: .02em;
  }
  button:disabled { opacity: .35; cursor: default; }
  button.primario { background: var(--tinta); color: var(--fundo); border-color: var(--tinta); }
  body.acerto button.primario, body.erro button.primario { background: #fff; color: #222; border-color: #fff; }
  .aviso { font-size: .85rem; color: var(--suave); padding: 0 1.6rem 1rem;
           max-width: 40rem; margin: 0 auto; width: 100%; }
</style>
</head>
<body>
<header><span>__TITULO__</span><span id="passo"></span></header>

<main>
  <div class="rotulo" id="rotulo">Écoutez</div>
  <div class="frase" id="frase"></div>
  <div class="traducao" id="traducao"></div>
  <div class="ouvido" id="ouvido"></div>
  <div class="certo" id="certo"></div>
  <div class="nota" id="nota"></div>
</main>

<div class="aviso" id="aviso"></div>

<footer>
  <button id="repetir">Répéter</button>
  <button id="agir" class="primario">Commencer</button>
</footer>

<script>
const DADOS = __DADOS__;

const $ = (id) => document.getElementById(id);
const corpo = document.body;
let i = -1;          // indice do item corrente
let estado = "inicio";

// --- voz: falar frances -------------------------------------------------
function falar(texto, lento) {
  return new Promise((resolve) => {
    if (!window.speechSynthesis) return resolve();
    speechSynthesis.cancel();
    const f = new SpeechSynthesisUtterance(texto);
    f.lang = "fr-FR";
    // Mesma velocidade do MP3 da licao: app e audio nao podem divergir, senao
    // o ouvido treina em dois ritmos e nenhum dos dois fixa.
    f.rate = lento ? DADOS.rate - 0.2 : DADOS.rate;
    f.onend = resolve;
    f.onerror = resolve;
    speechSynthesis.speak(f);
  });
}

// --- ouvir: reconhecimento ---------------------------------------------
const Reconhecimento = window.SpeechRecognition || window.webkitSpeechRecognition;
const TEM_MICROFONE = Boolean(Reconhecimento);

function ouvir() {
  return new Promise((resolve) => {
    if (!TEM_MICROFONE) return resolve(null);
    const r = new Reconhecimento();
    r.lang = "fr-FR";
    r.interimResults = false;
    r.maxAlternatives = 3;
    r.onresult = (e) => {
      const opcoes = [];
      for (const alt of e.results[0]) opcoes.push(alt.transcript);
      resolve(opcoes);
    };
    r.onerror = () => resolve(null);
    r.onend = () => resolve(null);
    r.start();
  });
}

// --- comparacao ---------------------------------------------------------
// Normaliza acento e pontuacao antes de comparar: o reconhecimento devolve
// "je voudrais un cafe s il vous plait" com grafia instavel, e reprovar por
// isso puniria pronuncia correta.
function limpar(s) {
  return s.toLowerCase()
    .normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
    .replace(/['’]/g, " ")
    .replace(/[^a-z0-9 ]/g, "")
    .replace(/\\s+/g, " ").trim();
}

function parecido(dito, alvo) {
  const a = limpar(dito).split(" ");
  const b = limpar(alvo).split(" ");
  if (!b.length) return false;
  const acertos = b.filter((p) => a.includes(p)).length;
  return acertos / b.length >= 0.7;   // 70% das palavras-alvo presentes
}

// --- fluxo --------------------------------------------------------------
function limparTela() {
  corpo.classList.remove("acerto", "erro");
  $("ouvido").textContent = "";
  $("certo").textContent = "";
  $("nota").textContent = "";
  $("traducao").textContent = "";
}

async function proximo() {
  limparTela();
  i += 1;
  if (i >= DADOS.itens.length) return terminar();

  const item = DADOS.itens[i];
  $("passo").textContent = (i + 1) + " / " + DADOS.itens.length;
  $("rotulo").textContent = "Répondez";
  $("frase").textContent = item.pergunta;
  $("agir").textContent = TEM_MICROFONE ? "Parler" : "Voir la réponse";
  estado = "pergunta";
  await falar(item.pergunta);
}

async function responder() {
  const item = DADOS.itens[i];

  if (!TEM_MICROFONE) return revelar(item, null, null);

  $("rotulo").textContent = "J'écoute…";
  $("agir").disabled = true;
  const opcoes = await ouvir();
  $("agir").disabled = false;

  if (!opcoes) return revelar(item, null, null);
  const acertou = opcoes.some((o) => parecido(o, item.resposta));
  revelar(item, opcoes[0], acertou);
}

async function revelar(item, dito, acertou) {
  estado = "resposta";
  if (dito) $("ouvido").innerHTML = "Vous avez dit : <b>" + dito + "</b>";
  if (acertou === true) corpo.classList.add("acerto");
  if (acertou === false) corpo.classList.add("erro");

  $("rotulo").textContent = acertou === true ? "C'est ça" : "On dit";
  $("certo").textContent = item.resposta;
  if (item.nota) $("nota").textContent = item.nota;
  if (item.traducao) $("traducao").textContent = item.traducao;
  $("agir").textContent = "Suivant";

  await falar(item.resposta);
  await falar(item.resposta, true);
}

function terminar() {
  limparTela();
  $("passo").textContent = "";
  $("rotulo").textContent = "Terminé";
  $("frase").textContent = "C'est tout pour aujourd'hui.";
  $("traducao").textContent = "Reescute o MP3 caminhando — é lá que fixa.";
  $("agir").textContent = "Recommencer";
  estado = "fim";
}

$("agir").addEventListener("click", () => {
  if (estado === "inicio" || estado === "resposta") return proximo();
  if (estado === "pergunta") return responder();
  if (estado === "fim") { i = -1; return proximo(); }
});

$("repetir").addEventListener("click", () => {
  const alvo = estado === "resposta" ? DADOS.itens[i].resposta : $("frase").textContent;
  falar(alvo, true);
});

$("frase").textContent = DADOS.titulo;
$("traducao").textContent = DADOS.itens.length + " frases para responder em voz alta.";
if (!TEM_MICROFONE) {
  $("aviso").textContent =
    "Este navegador não reconhece fala. O app funciona, mas quem julga a resposta é você — " +
    "para o veredito automático, abra no Chrome do computador.";
}
</script>
</body>
</html>
"""


def como_html(licao: Licao) -> str:
    """Devolve o app da licao como um unico arquivo HTML."""
    dados = {
        "titulo": licao.titulo,
        "rate": _rate(licao.velocidade),
        "itens": _itens(licao),
    }
    return _HTML.replace("__TITULO__", licao.titulo).replace(
        "__DADOS__", json.dumps(dados, ensure_ascii=False)
    )


def _rate(velocidade: str) -> float:
    """Converte a velocidade do edge-tts ("-15%") no rate da Web Speech (0.85)."""
    return round(1 + int(velocidade.rstrip("%")) / 100, 2)


def _itens(licao: Licao) -> list[dict[str, str]]:
    """Extrai o que o app consegue COBRAR do aluno.

    Producao vira pergunta direta. O par do semaforo tambem entra: pedir a forma
    nativa e a forma mais util de treinar justamente onde ele erra -- e a nota
    explica depois, nunca antes.
    """
    itens: list[dict[str, str]] = []
    for bloco in licao.blocos:
        if bloco.tipo == "producao":
            for item in bloco.itens:
                itens.append({"pergunta": item["pergunta"], "resposta": item["resposta"]})
        elif bloco.tipo == "semaforo":
            for item in bloco.itens:
                itens.append(
                    {
                        "pergunta": f"Comment dit-on, correctement : « {item['errado']} » ?",
                        "resposta": item["certo"],
                        "nota": item.get("nota_pt", ""),
                    }
                )
    return itens
