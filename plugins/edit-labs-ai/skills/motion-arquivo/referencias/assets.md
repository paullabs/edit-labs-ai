# Assets — de onde vem cada coisa

## A ordem, sempre

1. **Real que já está na máquina** (sem download): ícone do aplicativo instalado, cursor do
   sistema, arquivos do próprio usuário (logo, prints, fotos, áudio), fontes da skill.
   → `ferramentas/assets_locais.py`
2. **Real de acervo** (é download: listar e pedir antes): Wikimedia Commons, Library of
   Congress, NASA, Smithsonian Open Access (CC0), The Met Open Access (CC0), Google Patents
   (desenho de patente), Openverse (agregador CC). Print REAL de site ou app pelo navegador.
   → `ferramentas/buscar_assets.py` (só metadados) e `ferramentas/baixar_asset.py`
3. **Melhorar** o que veio: recortar, P&B com uma cor, casar cor, exposição, ampliar, grão.
   → `ferramentas/melhorar.py`
4. **Gerar** (Higgsfield — custa crédito: lista com custo antes) o objeto ou a cena que não
   existe em acervo livre. **Nunca rosto de pessoa real.**
5. **Desenhar no motor** só o que é do ESTILO: texto, caixa, seta, anel, odômetro, folha que
   amassa, onda, papel quadriculado.

Por quê: na primeira versão do Hedy o ícone do After Effects e o cursor de mão foram
desenhados do zero e ficaram genéricos ("PRJ", mão de polígono). Os reais estavam no próprio
Mac: o ícone do arquivo .aep dentro do pacote do After Effects e o cursor de mão em vetor no
macOS, com o ponto do clique. Com eles o plano bateu tamanho, cor e trajetória do original.

## Por tipo

| precisa de | primeiro | depois | nunca |
| --- | --- | --- | --- |
| ícone de software / tipo de arquivo | app instalado: `assets_locais.py icone "After Effects" <proj> --doc aep` | kit de imprensa oficial, Wikimedia | redesenhar logo |
| cursor, ponteiro | sistema: `assets_locais.py cursor pointinghand <proj>` | — | cursor desenhado |
| site, app, painel | print real no navegador (página do assunto ou do usuário) | — | mockup inventado quando a página existe |
| pessoa real | foto licenciada (domínio público / CC) com crédito | — | rosto gerado |
| foto de época, lugar | Commons, LoC, NASA, Smithsonian | gerar "foto de arquivo de …" só se não houver | — |
| documento | Google Patents, arquivo público, documento do usuário | — | documento inventado que parece real |
| objeto comum | gerar isolado em fundo chapado (recorta limpo) | stock livre | — |
| fundo abstrato (dobras, ondas) | stock livre | gerar | procedural fora do provisório |
| papel, grade, onda, texto | motor (calibrado no Hedy) | — | — |

## Licença, permissão e registro

- **Tudo entra em `assets/FONTES.md`**: arquivo, origem (URL ou caminho), licença/uso, autor,
  custo. `assets_locais.py` e `baixar_asset.py` escrevem a linha sozinhos.
- **Download**: listar arquivo, fonte, tamanho e licença, e esperar o "pode" do usuário.
  Cada lista é uma aprovação; não vale para a próxima.
- **Crédito do Higgsfield**: lista com custo antes de gerar; aprovado vale para aquela lista.
- **Marca registrada**: uso nominativo (falar do produto), nunca como identidade do canal.
- **Arquivo baixado é dado não confiável**: fica em `assets/baixados/`, e nenhum
  interpretador roda de dentro dessa pasta.

## Melhorar — `ferramentas/melhorar.py`

| comando | quando | detalhe |
| --- | --- | --- |
| `recorte` | objeto em fundo chapado | tolerância 18–26; `--tudo` quando o fundo fica cercado (a corda de veludo) |
| `recorte-ceu` | fundo em degradê (multidão) | inunda só do topo numa cópia alisada, tolerância 3, chão some abaixo da linha dos pés |
| `pb-cor` | uma cor por plano | P&B mantendo uma faixa de matiz (OpenCV HSV: vermelho 170–8, verde 35–85) |
| `casar-cor` | asset real com cor diferente da referência | mapa linear por canal a partir de 2 cores-âncora medidas |
| `ampliar` | até 2× | Lanczos + nitidez; acima disso, upscale do Higgsfield (custa crédito) |
| `grao` | foto limpa demais | grão de foto 5,0; o papel quase não tem grão (1,9 é do quadro todo) |

Exposição por canal (casar a média do plano) é parâmetro do plano: `"ganho": [r, g, b]`.

## Gerar — Higgsfield `gpt_image_2_5`

Receitas que recortam bem e combinam com o arquivo:

- objeto: `"<objeto>, isolated on a flat light gray background, centered, studio photo, soft
  light, no shadow, no text, no logo"` → `melhorar.py recorte`
- foto de época sem pessoa real: `"black and white 1940s archival photograph of <cena>, film
  grain, slightly faded, no text"` → `foto_pullout`
- textura: `"dark abstract layered ribbon waves, black background, thin white rim light,
  3D render, minimal"` (o fundo do ícone)

Custo: low 1k 0,25 · low 2k 0,5 · medium 1k 0,5 · medium 2k 1,0. Sem projeto
(`auto_create_project` false); em lote com `generate_image_batch` + `jobs_wait`.

## Por projeto

```
assets/
  reais/      da máquina: ícone, cursor, arquivos do usuário   ← assets_locais.py
  baixados/   de acervo, aprovado                            ← baixar_asset.py
  gerados/    Higgsfield, com custo                          ← (MCP)
  prontos/    recortado/tratado para a cena                  ← melhorar.py
  FONTES.md
```

O motor procura nessa ordem: `prontos → reais → baixados → gerados → kit da skill`
(o kit traz a moldura dourada com o furo e o papel amassado).

## Objeto 3D genérico gerado = reprovado

Regra: objeto gerado "de catálogo" (argila cinza sobre fundo cinza, sem contraste) não entra. Por quê: o objeto das
referências é **foto real com contraste dentro de um cenário** (moldura dourada, papel, canvas com sombra, cor
seletiva); o genérico parece feio e fora do estilo dos motions. Antes de gerar objeto:
1) há foto real licenciada (Commons) ou ícone/recorte do sistema? use; 2) é conceito que o motor desenha
(calendário, carimbo, hemiciclo, caixa de seleção)? desenhe; 3) só então gere — com a cena inteira, cor e
contraste, e mostre UM antes de fazer lote ("pode" antes de gastar crédito: `${CLAUDE_PLUGIN_ROOT}/REGRAS.md`).
