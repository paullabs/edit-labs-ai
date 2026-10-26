"""di — ponto de entrada. Despacha subcomandos para os módulos de scripts/.

Nunca rode `python3 scripts/...` direto: use o comando `di` do plugin (bin/di, no PATH do Claude Code).
"""
from __future__ import annotations

import sys

from comum import DIError

COMANDOS = {
    # instalação
    "instalar": ("instalar", "Não instala nada: o ambiente vem do editlabs-setup; só roda a verificação"),
    "verificar": ("instalar", "Checagem de instalação (ffmpeg, Python, módulos, skills irmãs, agentes)"),
    # F0–F1
    "preparar": ("preparar", "Cria o projeto a partir do bruto e lança a leitura em segundo plano"),
    "transcrever": ("transcrever", "Transcrição palavra a palavra (normalmente lançada pelo preparar)"),
    "silencio": ("silencio", "Mede piso de ruído, silêncios, vãos e energia por palavra"),
    "retakes": ("retakes", "Frases, grupos de tomadas, retake parcial, bastidor, hesitações (só SUGERE)"),
    "digest": ("digest", "O que o Editor lê: uma linha por frase; --janela a-b; --parte N"),
    # F2–F3
    "amostrar": ("amostrar", "TOMADAS.jpg: 1 quadro por tomada escolhida"),
    "edl": ("edl", "decisoes.json -> edl.json + MARCAS.md + roteiro_montado.txt"),
    "render": ("render_corte", "Renderiza o corte base (crop por rosto, ganho, punch-in)"),
    "verificar-corte": ("verificar_corte", "Checagens V24–V42 sobre o corte renderizado"),
    "auditar": ("auditar", "Auditoria frase a frase do corte: tempo no corte e no bruto, o que o render diz, alertas"),
    "exportar": ("exportar", "--motion-vox | --srt | --xmeml | --corte-viral"),
    # revisão e memória
    "autorrejeitar": ("autorrejeitar", "A lista de auto-rejeição da fase, por código, antes de chamar revisor"),
    "pacote-leigo": ("pacote_leigo", "Monta o pacote cego do Revisor Leigo"),
    "leigo": ("revisor", "Revisor Leigo em processo separado (claude -p)"),
    "diretor": ("revisor", "Diretor em processo separado (claude -p), p.ex. D4"),
    "laudo": ("laudo", "validar | render | gravar"),
    "portao": ("portao", "status | pode-avancar | abrir-tentativa | fechar | responder"),
    "status": ("portao", "= portao status"),
    "autorizar-imagens": ("portao", "Autoriza N imagens (grava 07_assets/.autorizado.json)"),
    "diario": ("portao", "Acrescenta entrada numerada no DIARIO.md"),
    # F4–F7 (motion-vox orquestrada)
    "iniciar-motion": ("motion", "Monta motion/<id>/ (projeto motion-vox padrão, V e H) a partir do corte aprovado"),
    "mv": ("motion", "Roda um script da motion-vox na cópia do projeto (ou --sync)"),
    "verificar-plano": ("motion", "V43–V52 e a régua E1–E9 sobre PLANO_MOTION.md"),
    "verificar-motion": ("motion", "Piloto (--trecho t0 t1) e master (--master): fala, nada parado, legenda, formato"),
    "entregar": ("motion", "Copia para <projeto>/FINAIS (ou DI_FINAIS), escreve RESUMO.md"),
    "_pipeline": ("preparar", None),
}


def ajuda() -> None:
    print("di — decupagem-inteligente\n\nComandos:")
    for k, (_, h) in COMANDOS.items():
        if h:
            print(f"  {k:<18} {h}")
    print("\nTodo comando aceita --projeto PASTA; sem ele, usa a pasta atual ou a lista de projetos do usuário\n($EDITLABS_DATA/decupagem-inteligente/projetos.json).")


def main(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "ajuda"):
        ajuda()
        return 0
    cmd, resto = argv[0], argv[1:]
    if cmd not in COMANDOS:
        print(f"comando desconhecido: {cmd}\n", file=sys.stderr)
        ajuda()
        return 2
    mod = __import__(COMANDOS[cmd][0])
    try:
        return int(mod.main(cmd, resto) or 0)
    except DIError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
