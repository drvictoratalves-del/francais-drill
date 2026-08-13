# francais-drill

Drill de francês por áudio. Um YAML de lição vira **MP3** (para caminhar) e um **app de voz no
navegador** (para treinar falando).

O método veio da análise de um anúncio do `praktika.ai`, em 12/08/2026: o loop
**pergunta → tentativa → "Presque" → forma nativa**. O avatar 3D ficou de fora — é a parte cara
e a que menos ensina.

**Treinar agora:** https://drvictoratalves-del.github.io/francais-drill/

## O que o verde significa — e o que não significa

O app compara **palavras**, não pronúncia: normaliza os acentos e marca verde quando 70% das
palavras-alvo aparecem na transcrição. Reconhecedor de fala é projetado para *perdoar* sotaque,
então os sons que mais separam um lusófono de um nativo — o /y/ de *tu*, o /ø/ de *peut* — são
justamente os que ele deixa passar. Verde quer dizer "as palavras certas saíram", nada além.

## Uso

    python frances_para_audio.py licoes/frances/01.yaml
    python frances_para_audio.py licoes/frances/01.yaml --saida ./saida --sem-pdf --sem-app

Sem `--saida`, grava na pasta de Áudios de Estudo do OneDrive.

## Testes

    python -m pytest -q

## Lições

- `01` — Combinar de sair (A2, fala a −15%) — entrada da rampa
- `05` — Discordar sem brigar (B1+) — mais adiante

As lições são calibradas para o **ouvido**, não para o olho: frases de 4 a 7 palavras, uma
estrutura por vez. Velocidade e conteúdo mudam no YAML, sem tocar em código.

## Publicação

`docs/` é servido por GitHub Pages. O microfone exige contexto seguro: por `file://` o navegador
não chega a pedir permissão, e é por isso que o app precisa de HTTPS para rodar no celular.

O `docs/index.html` é escrito à mão — lição nova exige uma linha nova ali.
