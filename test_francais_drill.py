"""Testes do drill de frances.

O teste central nao e tecnico, e PEDAGOGICO: a forma errada e dita UMA vez e a
forma correta ao menos TRES. No video que originou o projeto (praktika.ai) o
veredito e uma cor na tela -- vista e esquecida. No fone nao ha cor, e o erro
ouvido varias vezes FIXA. A regra e a defesa contra esse modo de falha, e por
isso ela e verificada por teste em vez de por disciplina.

Spec: docs/superpowers/specs/2026-08-12-drill-frances-audio-design.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from francais_drill.app import como_html  # noqa: E402
from francais_drill.escrever import como_markdown  # noqa: E402
from francais_drill.licao import LicaoInvalidaError, carregar  # noqa: E402
from francais_drill.montar import (  # noqa: E402
    PAUSA_DECOMPOSICAO,
    PAUSA_PRODUCAO,
    Fala,
    Pausa,
    lento,
    montar,
)

# --------------------------------------------------------------------------
# Fixture: licao deliberadamente NAO medica.
#
# O CLAUDE.md deste repo e inteiramente medico e puxa todo exemplo para a
# clinica sem que ninguem decida isso. O Dr. Victor cortou esse enquadramento
# em 12/08/2026: "sou uma pessoa alem de medico de dor". Regua registrada em
# memoria: um estranho lendo o material nao deve adivinhar a profissao dele.
# --------------------------------------------------------------------------

LICAO_YAML = """
id: "01"
titulo: "Pedir um cafe"
nivel: "A2"
cena:
  - "Bonjour, je voudrais un cafe, s'il vous plait."
  - "Bien sur. Ce sera tout ?"
blocos:
  - tipo: decomposicao
    itens:
      - fr: "Je voudrais un cafe."
        pt: "Eu gostaria de um cafe."
      - fr: "Ce sera tout ?"
        pt: "Sera so isso?"
  - tipo: semaforo
    itens:
      - errado: "Je veux un cafe."
        certo: "Je voudrais un cafe, s'il vous plait."
        nota_pt: "Querer direto soa brusco; o condicional e a cortesia padrao."
  - tipo: producao
    itens:
      - pergunta: "Comment tu commandes un cafe ?"
        resposta: "Je voudrais un cafe, s'il vous plait."
  - tipo: revisao
    itens:
      - fr: "Je m'appelle Victor."
        pt: "Meu nome e Victor."
"""


@pytest.fixture
def licao(tmp_path: Path):
    arq = tmp_path / "licao01.yaml"
    arq.write_text(LICAO_YAML, encoding="utf-8")
    return carregar(arq)


def _textos(passos) -> list[str]:
    return [p.texto for p in passos if isinstance(p, Fala)]


# --------------------------------------------------------------------------
# T3 -- a regra pedagogica. O teste mais importante do modulo.
# --------------------------------------------------------------------------


def test_forma_errada_dita_exatamente_uma_vez(licao):
    """Ouvir o erro repetido no fone FIXA o erro. Uma vez, nunca mais."""
    textos = _textos(montar(licao))
    assert textos.count("Je veux un cafe.") == 1


def test_forma_correta_dita_ao_menos_tres_vezes(licao):
    """A forma nativa precisa dominar a faixa em numero de repeticoes."""
    textos = _textos(montar(licao))
    assert textos.count("Je voudrais un cafe, s'il vous plait.") >= 3


def test_forma_correta_supera_a_errada_em_repeticoes(licao):
    """Invariante que sobrevive a mudanca de numeros absolutos."""
    textos = _textos(montar(licao))
    assert textos.count("Je voudrais un cafe, s'il vous plait.") > textos.count("Je veux un cafe.")


def test_erro_nunca_e_dito_sem_etiqueta_antes(licao):
    """Erro solto, sem 'On ne dit pas', vira modelo em vez de contraexemplo."""
    textos = _textos(montar(licao))
    i = textos.index("Je veux un cafe.")
    assert i > 0
    assert "ne dit pas" in textos[i - 1]


# --------------------------------------------------------------------------
# T2 -- o arco da faixa: a mesma cena crua abre e fecha
# --------------------------------------------------------------------------


def test_cena_crua_aparece_no_inicio_e_no_fim(licao):
    passos = montar(licao)
    textos = _textos(passos)
    primeira = licao.cena[0]
    ultima = licao.cena[-1]
    assert textos[0] == primeira
    assert textos[-1] == ultima


def test_cena_crua_e_identica_nas_duas_vezes(licao):
    """Se a cena final diferir da inicial, o termometro de progresso mente."""
    textos = _textos(montar(licao))
    n = len(licao.cena)
    assert textos[:n] == textos[-n:] == list(licao.cena)


# --------------------------------------------------------------------------
# T4 -- pausas: e nelas que o aluno fala. Sem pausa nao ha drill, so podcast.
# --------------------------------------------------------------------------


def test_cada_item_de_decomposicao_tem_pausa_para_repetir(licao):
    pausas = [p for p in montar(licao) if isinstance(p, Pausa) and p.blocos == PAUSA_DECOMPOSICAO]
    assert len(pausas) == 2  # a fixture tem 2 itens de decomposicao


def test_cada_item_de_producao_tem_pausa_mais_longa(licao):
    pausas = [p for p in montar(licao) if isinstance(p, Pausa) and p.blocos == PAUSA_PRODUCAO]
    assert len(pausas) == 1


def test_pausa_de_producao_e_maior_que_a_de_decomposicao():
    """Produzir do zero custa mais tempo que repetir o que se acabou de ouvir."""
    assert PAUSA_PRODUCAO > PAUSA_DECOMPOSICAO


def test_resposta_da_producao_vem_depois_da_pausa_nunca_antes(licao):
    """Resposta antes da pausa entrega o gabarito e anula o exercicio."""
    passos = montar(licao)
    i_pergunta = next(
        i for i, p in enumerate(passos) if isinstance(p, Fala) and p.texto.startswith("Comment tu")
    )
    assert isinstance(passos[i_pergunta + 1], Pausa)


# --------------------------------------------------------------------------
# Vozes -- o semaforo do video traduzido para o ouvido
# --------------------------------------------------------------------------


def test_frances_e_dito_por_voz_francesa(licao):
    falas_fr = [p for p in montar(licao) if isinstance(p, Fala) and p.texto in licao.cena]
    assert all(p.voz.startswith("fr-FR") for p in falas_fr)


def test_notas_em_portugues_usam_voz_brasileira(licao):
    nota = "Querer direto soa brusco; o condicional e a cortesia padrao."
    fala = next(p for p in montar(licao) if isinstance(p, Fala) and p.texto == nota)
    assert fala.voz.startswith("pt-BR")


def test_forma_correta_e_repetida_ao_menos_uma_vez_em_ritmo_lento(licao):
    alvo = "Je voudrais un cafe, s'il vous plait."
    devagar = lento(licao.velocidade)
    lentas = [
        p
        for p in montar(licao)
        if isinstance(p, Fala) and p.texto == alvo and p.velocidade == devagar
    ]
    assert len(lentas) >= 1


# --------------------------------------------------------------------------
# Velocidade -- calibrada pelo OUVIDO, que esta atras da leitura.
# Defeito medido em 12/08/2026: a primeira faixa saiu em ritmo quase natural
# e o Dr. Victor a achou dificil para um inicio.
# --------------------------------------------------------------------------


def test_frances_da_licao_de_entrada_fala_abaixo_do_natural(licao):
    """Padrao -15%: nao e preferencia, e a rampa de entrada."""
    assert licao.velocidade == "-15%"
    falas_fr = [p for p in montar(licao) if isinstance(p, Fala) and p.voz.startswith("fr-FR")]
    assert all(p.velocidade in (licao.velocidade, lento(licao.velocidade)) for p in falas_fr)


def test_portugues_nunca_desacelera(licao):
    """A instrucao sai do caminho rapido; so o frances e material de treino."""
    falas_pt = [p for p in montar(licao) if isinstance(p, Fala) and p.voz.startswith("pt-BR")]
    assert falas_pt
    assert all(p.velocidade == "+0%" for p in falas_pt)


def test_licao_pode_declarar_a_propria_velocidade(tmp_path: Path):
    """A rampa sobe no YAML, sem tocar codigo."""
    arq = tmp_path / "rapida.yaml"
    arq.write_text(LICAO_YAML + '\nvelocidade: "+0%"\n', encoding="utf-8")
    assert carregar(arq).velocidade == "+0%"


@pytest.mark.parametrize("normal,esperado", [("-15%", "-35%"), ("+0%", "-20%"), ("+10%", "-10%")])
def test_lento_acompanha_a_velocidade_corrente(normal, esperado):
    """Distancia RELATIVA: com valor fixo, os dois ritmos colapsariam quando a
    licao ficasse rapida, e a repeticao lenta deixaria de ensinar."""
    assert lento(normal) == esperado


# --------------------------------------------------------------------------
# T1 -- licao malformada falha ALTO, nomeando o campo. Nunca MP3 parcial.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "yaml_ruim,campo",
    [
        ('id: "01"\ntitulo: "x"\nnivel: "A2"\nblocos: []\n', "cena"),
        ('id: "01"\nnivel: "A2"\ncena: ["a"]\nblocos: []\n', "titulo"),
        (
            'id: "01"\ntitulo: "x"\nnivel: "A2"\ncena: ["a"]\n'
            "blocos:\n  - tipo: inexistente\n    itens: []\n",
            "inexistente",
        ),
        (
            'id: "01"\ntitulo: "x"\nnivel: "A2"\ncena: ["a"]\n'
            "blocos:\n  - tipo: semaforo\n    itens:\n      - errado: 'a'\n",
            "certo",
        ),
    ],
)
def test_licao_malformada_falha_nomeando_o_campo(tmp_path: Path, yaml_ruim: str, campo: str):
    arq = tmp_path / "ruim.yaml"
    arq.write_text(yaml_ruim, encoding="utf-8")
    with pytest.raises(LicaoInvalidaError) as erro:
        carregar(arq)
    assert campo in str(erro.value)


# --------------------------------------------------------------------------
# Texto de acompanhamento -- mesma fonte de dados que o audio
# --------------------------------------------------------------------------


def test_markdown_traz_a_cena_inteira(licao):
    md = como_markdown(licao)
    for linha in licao.cena:
        assert linha in md


def test_markdown_traz_o_par_erro_e_acerto(licao):
    md = como_markdown(licao)
    assert "Je veux un cafe." in md
    assert "Je voudrais un cafe, s'il vous plait." in md


def test_markdown_avisa_para_escutar_antes_de_ler(licao):
    """Ler antes de escutar anula o treino de ouvido -- o aviso vai impresso."""
    assert "Escute primeiro" in como_markdown(licao)


def test_markdown_nao_usa_dois_pontos_na_prosa_portuguesa(licao):
    """`lang: fr` faz o pandoc por espaco fino antes de `:` -- certo em frances,
    errado em portugues. Defeito medido no PDF da licao 1 em 12/08/2026."""
    md = como_markdown(licao)
    assert "Não se diz:" not in md
    assert "Diz-se:" not in md


# --------------------------------------------------------------------------
# App -- mesma fonte de dados, terceira saida
# --------------------------------------------------------------------------


def test_app_cobra_os_itens_de_producao(licao):
    html = como_html(licao)
    assert "Comment tu commandes un cafe ?" in html


def test_app_cobra_a_forma_nativa_do_semaforo(licao):
    """Pedir a forma certa e o treino mais util justamente onde ele erra."""
    html = como_html(licao)
    assert "Je voudrais un cafe, s'il vous plait." in html


def test_app_e_autocontido(licao):
    """Um arquivo, sem servidor, sem build: vai para o OneDrive e abre por clique."""
    html = como_html(licao)
    assert html.lstrip().startswith("<!DOCTYPE html>")
    assert "<script" in html and "src=" not in html.split("<script")[1][:200]


def test_app_declara_idioma_frances_para_a_sintese(licao):
    assert 'lang = "fr-FR"' in como_html(licao)


def test_app_fala_na_mesma_velocidade_do_mp3(licao):
    """App e audio divergentes treinariam o ouvido em dois ritmos."""
    assert '"rate": 0.85' in como_html(licao)  # -15% -> 0.85


def test_app_avisa_quando_nao_ha_reconhecimento_de_fala(licao):
    """Sem microfone o app cai para autoavaliacao E DIZ isso -- tela muda que
    nao responde e nao explica e o pior desfecho possivel."""
    assert "não reconhece fala" in como_html(licao)


def test_cena_vazia_e_invalida(tmp_path: Path):
    """Sem cena nao ha arco -- e o arco e o unico termometro de progresso."""
    arq = tmp_path / "sem_cena.yaml"
    arq.write_text('id: "01"\ntitulo: "x"\nnivel: "A2"\ncena: []\nblocos: []\n', encoding="utf-8")
    with pytest.raises(LicaoInvalidaError):
        carregar(arq)
def test_asset_de_silencio_acompanha_o_pacote():
    """O gerador le este mp3 em runtime. Sem ele o programa quebra com os testes verdes --
    foi o que aconteceu ao mudar o projeto de lugar em 13/08/2026."""
    from francais_drill.gerar import _ARQ_SILENCIO
    assert _ARQ_SILENCIO.exists(), f"asset ausente: {_ARQ_SILENCIO}"



# --------------------------------------------------------------------------
# v2 -- YAML estendido, 4 estagios, audio real/timestamps, blocos e indice
# --------------------------------------------------------------------------


def test_duracao_mp3_mede_asset_de_silencio():
    """duracao_mp3 deve medir o asset real de 700 ms sem depender de ffmpeg."""
    from francais_drill.gerar import _ARQ_SILENCIO, duracao_mp3

    dur = duracao_mp3(_ARQ_SILENCIO.read_bytes())
    assert 0.5 <= dur <= 0.9


def test_licao_v2_campos_opcionais_e_validacao(tmp_path: Path):
    arq = tmp_path / "aula.yaml"
    arq.write_text(
        LICAO_YAML
        + """
bloco: "1 · Sobrevivência"
tipo: "aula"
ordem: 1
foco: "Pedir café com cortesia"
vocabulario:
  - fr: "un café"
    pt: "um café"
pronuncia:
  - fr: "Je voudrais un café."
    pt: "Eu gostaria de um café."
    dica: "Mantenha o s final de voudrais mudo."
fala_livre:
  enunciado: "Peça um café sem ler."
  passos: ["Cumprimente", "Peça com je voudrais"]
  criterio: "Pedido claro"
  duracao_alvo_s: 45
""",
        encoding="utf-8",
    )
    lic = carregar(arq)
    assert lic.bloco == "1 · Sobrevivência"
    assert lic.tipo == "aula"
    assert lic.ordem == 1
    assert len(lic.vocabulario) == 1
    assert lic.pronuncia[0]["dica"].startswith("Mantenha")
    assert lic.fala_livre["duracao_alvo_s"] == 45

    ruim = tmp_path / "ruim_tipo.yaml"
    ruim.write_text(LICAO_YAML + '\ntipo: "podcast"\n', encoding="utf-8")
    with pytest.raises(LicaoInvalidaError) as err:
        carregar(ruim)
    assert "tipo" in str(err.value)


def test_todas_licoes_do_repositorio_passam_invariantes_pedagogicas():
    """Todo YAML publicado em licoes/frances/ precisa carregar e cumprir T2 + T3."""
    pasta = Path(__file__).parent / "licoes" / "frances"
    arquivos = sorted(pasta.glob("*.yaml"))
    assert len(arquivos) >= 8

    for arq in arquivos:
        lic = carregar(arq)
        passos = montar(lic)
        textos = _textos(passos)
        n = len(lic.cena)
        assert textos[:n] == textos[-n:] == list(lic.cena), f"arco quebrado em {arq.name}"
        for bloco in lic.blocos:
            if bloco.tipo == "semaforo":
                for item in bloco.itens:
                    assert textos.count(item["errado"]) == 1, f"erro repetido em {arq.name}: {item['errado']}"
                    assert textos.count(item["certo"]) >= 3, f"certo insuficiente em {arq.name}: {item['certo']}"


def test_montar_bloco_encadeia_licoes_com_separador(licao):
    from francais_drill.montar import montar_bloco

    passos = montar_bloco([licao, licao])
    textos = _textos(passos)
    assert textos[0].startswith("Lição 01.")
    assert textos.count("Je veux un cafe.") == 2  # 1 por licao


def test_app_v2_traz_4_estagios_gravacao_ab_gemini_e_notion(licao):
    midia = {
        "cena_src": "./audio/teste_cena.mp3",
        "cena_duracao": 12.5,
        "cena_tempos": [[0.0, 5.5], [6.2, 12.5]],
        "treino_src": "./audio/teste_treino.mp3",
        "clips": {"-15%|Je voudrais un cafe.": [0.0, 2.0]},
        "vel_normal": "-15%",
        "vel_lento": "-35%",
    }
    html = como_html(licao, midia=midia)
    for esperado in (
        "1 · Escuta",
        "2 · Pronúncia",
        "3 · Drill",
        "4 · Fala livre",
        "Comparar A/B",
        "gemini-3.8-flash",
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        "Copiar resumo para o Notion",
        "./audio/teste_cena.mp3",
        "francais_drill_erros_v1",
    ):
        assert esperado in html


def test_gerar_indice_agrupa_por_bloco_e_preserva_slugs_legados(licao):
    from francais_drill.site import gerar_indice_html, slug_arquivo

    assert slug_arquivo(licao) == "frances_01_pedir-um-cafe"
    from francais_drill.licao import Licao

    aula = Licao(id="aula-01", titulo="Aula 01 — Chegada", nivel="A1", cena=("Salut.",), blocos=())
    assert slug_arquivo(aula) == "aula-01_chegada"
    idx = gerar_indice_html(
        [
            {
                "id": "aula-01",
                "titulo": "Aula 01 — Chegada",
                "nivel": "A1 → A2",
                "bloco": "1 · Sobrevivência e Chegada (01–05)",
                "arquivo": "aula-01_chegada.html",
                "foco": "Apresentação",
                "duracao_s": 108,
            },
            {
                "id": "01",
                "titulo": "Combinar de sair",
                "nivel": "A2",
                "bloco": "Drills extras",
                "arquivo": "frances_01_combinar-de-sair.html",
                "foco": "Rampa",
                "duracao_s": 15,
            },
        ]
    )
    assert "1 · Sobrevivência e Chegada (01–05)" in idx
    assert "Drills extras" in idx
    assert "./aula-01_chegada.html" in idx
    assert "./frances_01_combinar-de-sair.html" in idx
    assert "Caderno de Erros" in idx
