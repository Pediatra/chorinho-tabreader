# 1001 — Imagem derivada para a trilha das mãos

Status: **provisório (agente)**. Tomada pelo agente da trilha das mãos em 2026-10-12, para
viabilizar o M0. Ainda não foi confirmada pelo dono.

## Contexto

O detector de mão do censo (MediaPipe HandLandmarker, `mediapipe==1.1.0`) e o detector de
rosto (YuNet, via `cv2.FaceDetectorYN`) precisam de pacotes que a imagem compartilhada
`chorinho:dev` não tem:

- `mediapipe`, que puxa `opencv-contrib-python`;
- as bibliotecas `libegl1`, `libgles2` e `libgl1`. Sem elas o MediaPipe 1.1.0 não carrega,
  porque exige `libEGL.so.1` (medido no build);
- os modelos `hand_landmarker.task` e `face_detection_yunet_2023mar.onnx`, que também não
  estão na imagem.

A `chorinho:dev` é a base da trilha tablatura (leitor, classificador, censo de presença).
Ela é construída de `Dockerfile` e usada pelo `compose.yaml`. Mudá-la para acomodar as
mãos muda o que a trilha tablatura já faz.

## Opções

1. Pôr `mediapipe==1.1.0` no `requirements.txt` compartilhado e reconstruir `chorinho:dev`.
2. Criar uma imagem derivada, `chorinho-maos:dev`, com `FROM chorinho:dev`, definida em
   `Dockerfile.maos` na raiz do repositório.
3. Instalar num venv no host. **Proibido pelo `AGENTS.md`**: tudo roda dentro do container,
   e o `.venv` do host serve só ao editor.

## Decisão

Opção 2. A imagem derivada é construída com:

```bash
podman build -t chorinho-maos:dev -f Dockerfile.maos .
```

## Consequências

- Dois builds: `chorinho:dev` (trilha tablatura) e `chorinho-maos:dev` (trilha das mãos).
  A derivada exige `chorinho:dev` já construída.
- A derivada não se atualiza sozinha. Quando a base mudar, ela precisa ser reconstruída.
- **Ressalva**: `pip install mediapipe` traz `opencv-contrib-python` (cv2 5.0.0), que convive
  com o `opencv-python-headless` da base. Por isso `chorinho-maos:dev` **não serve para a
  trilha tablatura**, e a trilha tablatura não deve rodar nela.
- Os modelos são baixados no build e fixados por sha256 na saída do `sha256sum` do log:
  `hand_landmarker.task` = `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1`;
  `face_detection_yunet_2023mar.onnx` = `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.
  Conferidos com `sha256sum` dentro da imagem construída em 2026-10-12.
- O modelo de pose (`pose_landmarker_full.task`) saiu do build: foi reprovado no piloto e
  não é usado.
- O `podman build` com contexto `.` envia `data/saida/` (2,8 GB), porque o `.dockerignore`
  tem o padrão `saida`, que vale só na raiz do contexto. Excluir `data/saida/` do contexto
  é decisão à parte.
- O `Dockerfile` antigo, em `data/saida/maos/imagem/Dockerfile`, continua no disco como
  rascunho. Não é versionado (`data/saida/` está no `.gitignore`). Apagá-lo é tarefa do dono.
