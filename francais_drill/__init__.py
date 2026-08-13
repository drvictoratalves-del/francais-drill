"""Drill de frances em audio: licao declarada em YAML -> MP3 bilingue.

    licao   -> carrega e VALIDA o YAML          (falha alto, nunca parcial)
    montar  -> licao para sequencia de passos   (puro, sem rede -- e onde mora a pedagogia)
    gerar   -> passos para MP3                  (edge-tts + juncao binaria)

A fronteira entre `montar` e `gerar` e o ponto do desenho: a regra pedagogica
("o erro e dito uma vez, o acerto tres") e verificavel por teste sem sintetizar
um unico byte, porque `montar` devolve dado, nao audio.

Nao modifica `audio_estudo`. Reaproveita dele apenas o asset de silencio e a
tecnica de juncao binaria; nao reusa `falar.sintetizar` porque aquela funcao
fatia o texto por regra de portugues e assume voz unica por arquivo -- o
oposto do que um drill bilingue precisa.

Spec: docs/superpowers/specs/2026-08-12-drill-frances-audio-design.md
"""
