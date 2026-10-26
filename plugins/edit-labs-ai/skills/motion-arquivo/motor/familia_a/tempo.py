"""
Grade de 10 qps.

Medido no Hedy: o conteudo muda a cada 3 quadros (51% das mudancas), sempre nos
quadros n % 3 == 2. Os CORTES tambem caem nessa grade (566, 617, 698). O grao congela
junto com o conteudo — o quadro inteiro anda a 10 qps, nao so as camadas animadas.
"""
FPS = 30
PASSO = 3
FASE = 2


def configurar(qps=10):
    """Cadencia do projeto: 10 qps (Hedy, passo 3, fase 2) ou 15 qps (galeria, passo 2, fase 0).
    Medido na galeria: o conteudo muda a cada 2 quadros (padrao =x=x), so o pouso dos jornais vai a 30."""
    global PASSO, FASE
    PASSO, FASE = {10: (3, 2), 15: (2, 0), 30: (1, 0)}[int(qps)]      # galeria: muda nos quadros pares (corte em 154)


def grade(n):
    """Ultimo quadro da grade <= n. Todo quadro mostra o estado amostrado aqui."""
    return n - ((n - FASE) % PASSO)


def degrau_seguinte(t):
    """Primeiro quadro da grade em t ou depois — onde a palavra falada aparece."""
    import math
    n = math.ceil(t * FPS - 1e-6)
    while n % PASSO != FASE:
        n += 1
    return n
