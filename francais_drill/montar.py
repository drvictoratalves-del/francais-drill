"""Converte a licao na sequencia de passos da faixa. Puro: nao toca a rede.

E aqui que mora a pedagogia -- e por isso e aqui que os testes mordem. Nenhuma
regra deste modulo depende de sintetizar audio, entao todas sao verificaveis
em milissegundos.

O video que originou o projeto codifica o veredito em COR: vermelho para a
forma que soa estrangeira, verde para a nativa, com a tela piscando. No fone
nao existe cor. A substituicao e etiqueta falada, mantendo tudo em voz
francesa -- decisao do Dr. Victor, contra a recomendacao inicial de usar voz
brasileira no erro; com dois anos de base o ouvido ja rejeita a forma estranha,
e a imersao vale mais que a protecao.

O que NAO muda: o erro e dito uma vez e nunca mais. Na tela, a forma errada e
vista e some; no fone, ela e ouvida e FIXA.
"""

from __future__ import annotations

from dataclasses import dataclass

from .licao import Licao

VOZ_FR = "fr-FR-DeniseNeural"
VOZ_PT = "pt-BR-AntonioNeural"

# O portugues das notas nunca varia: a instrucao precisa sair do caminho rapido.
# So o frances desacelera, e o quanto vem da licao (campo `velocidade`).
NORMAL = "+0%"

# Quanto a repeticao lenta fica ABAIXO da velocidade corrente da licao. Manter
# a distancia relativa, e nao um valor fixo, impede que os dois ritmos colapsem
# num so quando a licao ja estiver rapida.
DELTA_LENTO = 20

# Pausas em BLOCOS do asset de silencio de 700 ms, nao em segundos: o silencio
# e arquivo emendado em bytes, entao so multiplos exatos existem. Pedir "3,5 s"
# e pedir 5 blocos; expor o campo em segundos convidaria a arredondamento
# silencioso.
PAUSA_DECOMPOSICAO = 5  # 3,5 s -- repetir o que se acabou de ouvir
PAUSA_PRODUCAO = 6  # 4,2 s -- formular do zero custa mais
PAUSA_CAPITULO = 3  # 2,1 s -- respiro entre capitulos num MP3 de bloco

ETIQUETA_ERRO = "On ne dit pas :"
ETIQUETA_CERTO = "On dit :"


@dataclass(frozen=True)
class Fala:
    texto: str
    voz: str
    velocidade: str = NORMAL


@dataclass(frozen=True)
class Pausa:
    blocos: int


Passo = Fala | Pausa


def lento(velocidade: str) -> str:
    """Devolve a velocidade da repeticao lenta, DELTA_LENTO pontos abaixo."""
    return f"{int(velocidade.rstrip('%')) - DELTA_LENTO:+d}%"


def montar(licao: Licao) -> list[Passo]:
    """Devolve a faixa inteira como sequencia de falas e pausas."""
    vel = licao.velocidade
    devagar = lento(vel)
    passos: list[Passo] = []

    passos.extend(_cena(licao, vel))
    for bloco in licao.blocos:
        passos.extend(_MONTADORES[bloco.tipo](bloco.itens, vel, devagar))
    passos.extend(_cena(licao, vel))

    return passos


def montar_bloco(licoes: list[Licao]) -> list[Passo]:
    """Combina varias licoes num unico MP3 longo de caminhada com separadores falados."""
    if not licoes:
        raise ValueError("montar_bloco exige ao menos uma licao")

    passos: list[Passo] = []
    for indice, licao in enumerate(licoes):
        if indice > 0:
            passos.append(Pausa(PAUSA_CAPITULO))
        rotulo = "Leitura" if licao.tipo == "leitura" else "Lição"
        passos.append(Fala(f"{rotulo} {licao.id}. {licao.titulo}.", VOZ_PT))
        passos.append(Pausa(PAUSA_CAPITULO))
        passos.extend(montar(licao))
    return passos


def _cena(licao: Licao, vel: str) -> list[Passo]:
    """A cena crua, identica na abertura e no fecho.

    Diferenca entre as duas quebraria o unico termometro de progresso da faixa:
    o mesmo audio que era ruido aos 30 s volta no fim, compreensivel.
    """
    return [Fala(linha, VOZ_FR, vel) for linha in licao.cena]


def _decomposicao(itens, vel: str, devagar: str) -> list[Passo]:
    passos: list[Passo] = []
    for item in itens:
        passos.append(Fala(item["fr"], VOZ_FR, devagar))
        passos.append(Fala(item["pt"], VOZ_PT))  # o portugues nunca desacelera
        passos.append(Fala(item["fr"], VOZ_FR, vel))
        passos.append(Pausa(PAUSA_DECOMPOSICAO))
        passos.append(Fala(item["fr"], VOZ_FR, vel))
    return passos


def _semaforo(itens, vel: str, devagar: str) -> list[Passo]:
    """O nucleo do metodo. A contagem aqui e invariante, nao estilo."""
    passos: list[Passo] = []
    for item in itens:
        # O erro NUNCA aparece solto: sem a etiqueta antes, ele vira modelo.
        passos.append(Fala(ETIQUETA_ERRO, VOZ_FR, vel))
        passos.append(Fala(item["errado"], VOZ_FR, vel))  # <- unica ocorrencia

        passos.append(Fala(ETIQUETA_CERTO, VOZ_FR, vel))
        passos.append(Fala(item["certo"], VOZ_FR, vel))  # 1
        passos.append(Fala(item["certo"], VOZ_FR, devagar))  # 2
        if item.get("nota_pt"):
            passos.append(Fala(item["nota_pt"], VOZ_PT))
        passos.append(Fala(item["certo"], VOZ_FR, vel))  # 3
    return passos


def _producao(itens, vel: str, devagar: str) -> list[Passo]:  # noqa: ARG001
    passos: list[Passo] = []
    for item in itens:
        passos.append(Fala(item["pergunta"], VOZ_FR, vel))
        # A resposta vem DEPOIS da pausa. Antes, entregaria o gabarito.
        passos.append(Pausa(PAUSA_PRODUCAO))
        passos.append(Fala(item["resposta"], VOZ_FR, vel))
    return passos


def _revisao(itens, vel: str, devagar: str) -> list[Passo]:  # noqa: ARG001
    passos: list[Passo] = []
    for item in itens:
        passos.append(Fala(item["fr"], VOZ_FR, vel))
        passos.append(Fala(item["pt"], VOZ_PT))
    return passos


_MONTADORES = {
    "decomposicao": _decomposicao,
    "semaforo": _semaforo,
    "producao": _producao,
    "revisao": _revisao,
}
