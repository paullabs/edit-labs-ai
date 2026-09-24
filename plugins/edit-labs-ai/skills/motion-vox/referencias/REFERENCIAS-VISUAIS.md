# Referências visuais — abra ANTES de compor

> **Não vêm com o plugin:** os quadros e vídeos de terceiros que servem de referência ao kit (os 32 quadros do
> estudo Porsche, a Style Bible e o manual visual com os quadros da Vox, o vídeo de referência da legenda). O que
> eles ensinam está escrito nos `.md` desta pasta e medido em números — as faixas que `lib/medir.py` imprime como
> "faixa Bible" vêm da Style Bible. Para compor olhando, monte a sua pasta de referência (ver **Monte as suas
> referências**, no fim desta página) e troque as referências das tabelas pelas suas.


A skill compõe **olhando** a referência, não lembrando dela. Descrição em texto (`registros.md`,
`identidade.md`) diz o que fazer; só o frame na tela diz como fica. Antes de escrever cada `build_M#`, abra
os quadros de referência do registro da cena com a ferramenta Read.

Medido (`lib/medir.py`, mesma métrica nos dois lados): composição feita de memória costuma ficar em **massa
escura 3–7% e acento 0,1–0,8%**; a referência Porsche tem **15% e 5,0%**, e a faixa do estilo é 10–18% e
3–7%. A distância não é de gosto — é de faixa.

## Onde estão

| Fonte | Caminho | Formato |
| --- | --- | --- |
| Estudo Porsche (MOTION LADY) | quadros bf01–bf32 (não incluídos; `estudos/vox-porsche/ESTUDO.md` cita os principais e traz a URL de origem) | 32 frames 1280×720 + laudo em `ESTUDO.md` |
| Style Bible — 10 frames da Vox | o manual visual do kit (PDF, não incluído) | páginas 8–16, anotadas |
| Legenda (talking head, medida frame a frame) | um vídeo de referência de terceiros (não incluído) | vídeo 720×1280 |

## Por registro — onde olhar

| Registro (`registros.md`) | Referência do kit (não incluída) | O que copiar de lá |
| --- | --- | --- |
| **Mesa de pesquisa** | Bible p.8, p.9, p.13 · Porsche bf31, bf32 | props cortados nas bordas, círculo amarelo ATRÁS do herói, mesa em perspectiva com foco raso, fita amarela (não bege) |
| **Documentário retrô / CRT** | Bible p.15 · Porsche bf01, bf15, bf16 | curvatura de tubo, franja RGB nas 4 bordas, faixa amarela segurando o título, palavras-fantasma atrás |
| **Foto em cartão** | Bible p.11 · Porsche bf10, bf28, bf31 | margem branca grossa, nome em etiqueta amarela, círculo à mão em 2 passadas marcando a pessoa |
| **Foto em tela cheia** | Porsche bf14, bf19, bf25, bf27 · `hierarquia-e-profundidade.md` §3 | vinheta orgânica, lente amarela circular sobre a região citada, 1 foto por beat |
| **Dado a mão** | Bible p.12 | hachura de marcador, número escrito à mão, seta desenha a relação |
| **Gráfico de barra** | Porsche bf23 · Bible p.5 | barras carvão, grade AMARELA, fonte citada sob o título, círculo à mão marcando a leitura |
| **Documento de época / jornal** | Porsche bf13, bf20 | marca-texto amarelo em cascata (2–3 marcações guiando a leitura), foco raso nas bordas |
| **Diagrama explicativo** | Porsche bf22 · Bible p.10, p.14 | line art + lente amarela na parte citada + linha de chamada fina + etiqueta |
| **Processo** | Bible p.16 | uma linha é a espinha; 3–5 estágios; um recorte real por estágio |
| **Insert real / logo** | Porsche bf06, bf24 (recorte de pessoa com halo amarelo) | herói da janela (≥620px), citação em serif itálica ao lado |
| **Cartela de ano / marco** | Porsche bf05, bf09, bf12, bf25 | tela inteira, número em serif, sozinho — separador de capítulo |
| **Registro escuro** | Porsche bf09, bf26 · Bible p.5 | massa preta + um único ponto luminoso; resolve o déficit de massa escura |
| **Legenda queimada** | o vídeo de referência da legenda (`legenda.md` tem os números) | centrado, corte seco, 2,45 blocos/s, 94% branco |

## Como usar no fluxo

1. Etapa 2 (escolher frases): decida o registro de cada cena.
2. **Antes da etapa 5**: `Read` nos quadros de referência do registro, na sua pasta de referência. Dois ou
   três bastam.
3. Componha. Depois rode `python3 lib/medir.py 08_images/frames/M#_END.png` e compare
   com a linha "Porsche" da tabela em `ESTUDO.md` §2.
4. No laudo D2, cite **qual frame de referência** a cena está seguindo. Cena sem
   referência citada não passa.

## Ritmo — o que a referência mede e o kit ainda não faz

| | Porsche (medido) | Style Bible | kit hoje |
| --- | --- | --- | --- |
| cadência do desenho | **12 fps** (alterna 2–3 frames sobre 30) | props 12 fps | **12 fps, um relógio só** (desenho, boil e grão) |
| duração mediana de cena | 1,23 s | — | 2,3–5,3 s por cutaway |
| palavras por cena | 4,3 | — | ~8–14 |
| câmera | zoom em degraus por insert | drift 0,3–0,8%/s · pan 3–8% · parallax | push (`apply_camera`); `pan` e `drift` já no `kit`; parallax ainda não |

O relógio único a 12 fps é a proposta nº 1 do `ESTUDO.md` §8, aplicada no kit: `MOTION_FPS = 12` e `RELOGIO_UNICO = True` no bloco CLIPE; `V.BOIL_FPS` segue o relógio.

## Monte as suas referências

As referências de terceiros não vêm com o plugin. Para compor olhando, e não de memória, monte a sua pasta:

1. **3 a 5 vídeos** do estilo que você quer seguir.
2. **Um quadro de cada tipo de cena** (foto em cartão, objeto na mesa, diagrama, pessoa…) numa pasta
   `referencias/minhas/`, com o nome do registro. Troque os caminhos das tabelas acima por esses quadros.
3. **Os números**: paleta em hex, fontes (ou equivalentes livres), tamanho e posição do texto, quanto tempo cada
   cena segura, quanto do vídeo tem motion, como a legenda se comporta. `lib/medir.py` mede massa escura,
   acento e vazio nos quadros de referência e nos seus.
4. **As regras escritas**: que frase vira que cena, como entra e como sai, o que é proibido.
5. **Um kit base** (fundo, 3–5 objetos recorrentes, fontes com licença) e **moldes de prompt** com o DNA que
   todo asset novo precisa bater (`assets-sob-medida.md` §3).
6. **A sua régua de gosto, escrita**: troque a "Régua de gosto do kit" do `SKILL.md` pela sua.
