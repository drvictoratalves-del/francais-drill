# francais-drill
Drill de franc├¬s por ├íudio. Um YAML de li├º├úo vira **MP3** (para caminhar), **PDF** (para conferir
depois) e um **app HTML** (para treinar falando).
O m├⌐todo veio da an├ílise de um an├║ncio do `praktika.ai`, em 12/08/2026: o loop
**pergunta ΓåÆ tentativa ΓåÆ "Presque" ΓåÆ forma nativa**. O avatar 3D ficou de fora ΓÇö ├⌐ a parte cara
e a que menos ensina.
## Uso
    python frances_para_audio.py licoes/frances/01.yaml
    python frances_para_audio.py licoes/frances/01.yaml --saida ./saida --sem-pdf --sem-app
Sem `--saida`, grava na pasta de ├üudios de Estudo do OneDrive.
## Testes
    python -m pytest -q
## Li├º├╡es
- `01` ΓÇö Combinar de sair (A2, fala a ΓêÆ15%) ΓÇö entrada da rampa
- `05` ΓÇö Discordar sem brigar (B1+) ΓÇö mais adiante
As li├º├╡es s├úo calibradas para o **ouvido**, n├úo para o olho: frases de 4 a 7 palavras, uma
estrutura por vez. Velocidade e conte├║do mudam no YAML, sem tocar em c├│digo.
## Contexto
N├¡vel medido em 12/08/2026: B1 de leitura, travando na fronteira do B2. A escuta n├úo foi medida
e ├⌐ a hip├│tese de estar abaixo ΓÇö por isso o drill ├⌐ de ├íudio.
O registro de desenho fica fora deste repositorio: contem avaliacao pessoal de proficiencia.
## Risco conhecido
Nada aqui valida o franc├¬s. Erro de g├¬nero ou de acordo numa li├º├úo chega ao fone e ├⌐ praticado
em voz alta.