# francais-drill

Drill de francês por áudio. Um YAML de lição vira **MP3** (para caminhar) e um **app web em 4 estágios** (com áudio narrado real `fr-FR-DeniseNeural`, gravação A/B e avaliação opcional de pronúncia por IA).

O método veio da análise de um anúncio do `praktika.ai`, em 12/08/2026: o loop
**pergunta → tentativa → "Presque" → forma nativa**. O avatar 3D ficou de fora — é a parte cara
e a que menos ensina.

**Treinar agora:** https://drvictoratalves-del.github.io/francais-drill/

## Estágios no app web (v2)

1. **Escuta longa:** áudio narrado completo (`fr-FR-DeniseNeural`) com velocidade ajustável (`0.75×`, `0.85×`, `1.0×`), texto inicialmente oculto (*escute primeiro, leia depois*) e timestamps clicáveis frase a frase.
2. **Pronúncia (Shadowing & A/B):** falas-chave da lição com áudio nativo normal/lento, gravação da sua voz (`MediaRecorder` — funciona no iPhone/Safari, Android e Desktop), **comparação A/B** (Nativo → Minha voz), checagem lexical quando o navegador suportar e avaliação opcional de pronúncia por áudio via Gemini API (`gemini-3.8-flash`, chave salva apenas no `localStorage`).
3. **Drill (Semáforo & Resposta ativa):** `On ne dit pas` / `On dit` e perguntas diretas da cena com registro automático de itens difíceis no **Caderno de Erros** local.
4. **Fala livre:** missão oral (30–60 s), feedback opcional na rubrica e botão **Copiar resumo para o Notion**.

## O que o verde significa — e o que não significa

No Drill, o reconhecedor de fala do navegador compara **palavras**, não pronúncia: normaliza acentos e marca verde quando 70% das palavras-alvo aparecem na transcrição. Reconhecedor de fala é projetado para *perdoar* sotaque — então os sons que mais separam um lusófono de um nativo (o `/y/` de *tu*, o `/ø/` de *peut*, vogais nasais e *liaisons*) passam batido. Para avaliar som real, use **Comparar A/B** ou a avaliação por áudio com IA na aba **Pronúncia**.

## Uso

Gerar MP3 de caminhada (e PDF/HTML avulsos) de uma lição:

    python frances_para_audio.py licoes/frances/aula_01.yaml
    python frances_para_audio.py licoes/frances/aula_01.yaml --saida ./saida --sem-pdf

Compilar várias lições em um único MP3 longo contínuo de caminhada:

    python frances_para_audio.py --compilar-bloco licoes/frances/aula_0*.yaml --nome bloco-1 --saida ./saida

Construir o site completo em `docs/` (MP3s sincronizados em `docs/audio/`, páginas das lições, `docs/index.html` automático e PWA):

    python frances_para_audio.py --construir-site docs

## Testes

    python -m pytest -q

## Lições publicadas

- **1 · Sobrevivência e Chegada (01–05):** Aulas 01 a 05 (A1 → A2, voz `fr-FR-DeniseNeural` a −10%)
- **Leituras de Imersão:** *Une journée en ville* (30 frases narradas + laboratório de escuta e reconto)
- **Drills extras:** `01` — Combinar de sair (A2, −15%) e `05` — Discordar sem brigar (B1+)

## Publicação

`docs/` é servido por GitHub Pages (`main`). O microfone exige contexto seguro (HTTPS), e o `docs/index.html` agora é gerado automaticamente por `--construir-site docs` com manifesto PWA e cache offline de áudios ouvidos.
