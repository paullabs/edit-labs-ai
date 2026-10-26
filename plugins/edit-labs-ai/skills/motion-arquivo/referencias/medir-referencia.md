# Medir uma referência nova

Quando o pedido é "deixa igual a este vídeo", a impressão visual erra o que a medição acerta.

1. **Quadros** a 720 do original (`ffmpeg -i ref.mp4 -start_number 0 q/%04d.png`).
2. **Grade**: compare quadros vizinhos — se o conteúdo muda a cada 2 ou 3 quadros, é 15 ou
   10 qps de conteúdo. Ache a fase (`n % 3`).
3. **Cortes**: diferença média + histograma entre quadros (`ferramentas/comparar.py` faz).
4. **Por plano**, meça com a mesma régua o que o plano tem:
   - objeto conhecido por degrau (caixa, largura, centro) → curva de câmera e âncora do zoom;
   - texto: caixa da tinta, altura de maiúscula, brilho do núcleo (p90), borda 10–90%;
   - fonte: ranqueie candidatas pelo perfil de colunas;
   - cor média do plano e por elemento (âncoras para `casar-cor`);
   - fundo com contraste esticado ×5–7.
5. **Reconstrua e compare** passando o nosso pela MESMA entrega (720p ~1,26 Mbps).
6. Ajuste até bater; tabele os números no plano (como `EVERY_`, `P7_`, `P13_`, `P20_` do Hedy).

Ferramentas: `ferramentas/comparar.py` (cortes, cor, luz), `ferramentas/folha_quadros.py` (folha de contato) e
`ferramentas/montar_entrega.py` (lado a lado). O vídeo de referência fica na pasta do projeto, nunca no plugin: é de
terceiros e serve só para medir.
O exemplo completo de reprodução medida é `exemplo/hedy/`.
