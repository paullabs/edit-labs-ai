# Formatos — contratos em prosa

Os schemas em `schemas/` são a versão executável. `di edl` valida `decisoes.json` antes de ler; os outros são conferidos por `di verificar` e pelos testes do piloto.

## Relógios

- **Bruto:** segundos do arquivo de entrada (`palavras.json`, `retakes.json`, `decisoes.json`, `edl.json` `source_*`).
- **Corte:** segundos e frames da timeline montada (`edl.json` `timeline_*`, `palavras_corte.json`, `cortes.json`, SRT, XML).
- Nenhum número de tempo é digitado pelo modelo: o Editor escreve índices de frase e palavra; os scripts resolvem o tempo.

## Por arquivo

| Arquivo | Quem escreve | Conteúdo |
| --- | --- | --- |
| `01_transcript/palavras.json` (`di-palavras/1`) | `transcrever.py` | `palavras[{i, w, t, e, p, seg, spk, ambigua, sugerido?, w_confirmado?, realinhado?}]`, engine, modelo, parâmetros, glossário, sha do áudio |
| `01_transcript/silencios.json` | `silencio.py` | piso e limiar em dB, silêncios `{t, e, d}`, vãos entre palavras, RMS por palavra |
| `01_transcript/digest.md` | `digest.py` | uma linha por frase com marcas (legenda no topo do arquivo) |
| `02_decupagem/retakes.json` | `retakes.py` | `frases[]`, `grupos[{id, tomadas[{frase, tomada, tipo, metade_com?}], sugerida, regra, empate_com}]`, `retakes_parciais[]`, `sobreposicoes[]`, `fronteiras_sugeridas[]`, `resumo` |
| `02_decupagem/MAPA_DO_BRUTO.md` | Editor | bloco `yaml` `blocos[{id, assunto, t, e, regravacao?}]` + tabela `trecho | o que é` + notas de tomada + palavras a confirmar |
| `02_decupagem/<id>/decisoes.json` | **Editor** | ver `fases/2-decupagem.md`; schema `decisoes` |
| `02_decupagem/<id>/edl.json` (`di-edl/1`) | `edl.py` | `segmentos[{n, source_in/out, timeline_in_f/out_f, frames, palavra_in/out, texto, escala, ganho_db, crop_x, junta_in/out{tipo, modo, voz, silencio, respiro, folga_*, rms_local_db, ref_voz_db, relaxado, cobertura, residuo}, motivo}]`, `palavras_mantidas`, `fillers_tirados`, `pausas_preservadas`, `removido`, `duracao`, `frames_total` |
| `02_decupagem/<id>/MARCAS.md` | `edl.py` | frase → tomadas no bruto → escolhida → motivo → in/out → folga à voz · resíduo (respiro) → emenda |
| `02_decupagem/<id>/roteiro_montado.txt` | `edl.py` | `[n] texto` por segmento; é contra ele que F3 confere |
| `03_corte/<id>/verificacao.json` | `verificar_corte.py` | checks V24–V39 (`di-verificacao/1`) |
| `laudos/F<N>_V_verificador_t<k>.json` | todos os scripts | os checks da fase, por vídeo |
| `laudos/F<N>_<rubrica>_<papel>_t<k>[_<id>].md` | Diretor, Leigo, via `laudo gravar` | front matter YAML (schema `laudo`) + corpo; nunca sobrescrito |
| `laudos/pacote-leigo/F<N>/t<k>/<id>/` | `pacote_leigo.py` | F2: `roteiro.txt`. F3: `texto.txt`, `sobre.txt`, `ritmo.txt`, `juntas/`, pontas |
| `laudos/PORTAO_F<N>_t<k>.md` | Editor | a mensagem de portão, literal |
| `run-manifest.json` (`di-manifest/1`) | `portao.py` e os scripts | a única verdade do estado |
| `ESTADO.md` | `estado.py` | gerado; nunca editado à mão (hash no rodapé) |
| `DIARIO.md` | `di diario`, `portao.py` | entradas numeradas DECISÃO, RESPOSTA, TENTATIVA, NOTA |

## Laudo (front matter)

```yaml
laudo: C2            # C1–C4, D1–D5, L, L1, L2
alvo: 02_decupagem/03-prompt-claude/
fase: F2
tentativa: 1
isolamento: processo # processo | subagente | passe | chat_novo
escopo: li …
nao_visto: não assisti nem ouvi …
veredito: APROVADO   # APROVADO | APROVADO_COM_CORRECAO | REPROVADO
procurei: …          # obrigatório na t1 sem achado
achados:
  - severidade: HIGH # BLOCKER | HIGH | MEDIUM | LOW
    tipo: corte      # só no Leigo: corte | conteudo | pendencia
    item: …
    observacao: …
    correcao: …
    corrigido: false
proxima_etapa: …
```

Regras aplicadas por `laudo gravar`: BLOCKER aberto ou HIGH não corrigido → REPROVADO; HIGH/MEDIUM corrigido → APROVADO_COM_CORRECAO; verbo de escuta sem `escuta: humana` → recusado; no Leigo, `conteudo` e `pendencia` viram LOW e o veredito é recalculado por código.

## Nomes fixos

Comandos, arquivos e pastas são os da tabela §10.7 do PLANO.md. `di verificar` (item 13) recusa em `SKILL.md`, `fases/` e `papeis/` os nomes antigos: `di init`, `texto_pretendido`, `01_leitura/`, `07_entrega`, `PORTAO-F3`, `duvida: true`, `verificar_master.py`, `di motion`, `pacote_cego`, `DECISOES.md`, `ARMADILHAS-PROJETO`.
