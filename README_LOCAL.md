# VarVid — rodando 100% local

Esta versão roda tudo na sua máquina, **sem Modal e sem Render**. O mesmo web app
(`ui.html`), mas o render dos vídeos acontece localmente via `ffmpeg`.

## Por que a versão original não roda local

Os arquivos originais foram feitos para a nuvem:

- `server.py` (Flask) manda o render para o **Modal** (nuvem serverless).
- O Modal baixa seus takes e devolve os vídeos por uma URL pública do **Render**
  (`https://varvid.onrender.com`).

Ou seja: precisa de duas contas de nuvem, e o Modal **não consegue** falar com o
seu `localhost`. Por isso, para rodar local, use o `local_app.py` abaixo — ele
substitui o `server.py` e faz o render na sua máquina.

## Pré-requisito: ffmpeg

Precisa do `ffmpeg` (e `ffprobe`) instalados no sistema:

- **macOS:** `brew install ffmpeg`
- **Ubuntu/Debian:** `sudo apt install ffmpeg`
- **Windows:** baixe em https://www.gyan.dev/ffmpeg/builds/ e adicione ao PATH

Confirme com: `ffmpeg -version`

## Passo a passo

Coloque estes arquivos **na mesma pasta**:

```
local_app.py
ui.html              <- o seu (obrigatório, o app serve ele)
requirements_local.txt
```

Depois:

```bash
# 1. (recomendado) ambiente virtual
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. dependências
pip install -r requirements_local.txt

# 3. rodar
python local_app.py
```

Abra **http://localhost:5000** no navegador. Arraste seus takes, escolha o número
de variações, escreva o headline (opcional) e clique em gerar. Os vídeos aparecem
prontos para baixar.

## Recursos opcionais (degradam com elegância)

O app funciona só com `flask` + `ffmpeg`. As libs abaixo são opcionais:

- **`opencv-python-headless` + `mediapipe==0.10.9`** → habilitam o **zoom com
  detecção de rosto**. Sem elas, o zoom fica centralizado (funciona igual).
- **Fonte para o headline**: o app procura automaticamente Poppins, DejaVu, Arial
  etc. Se não achar nenhuma, o headline é desativado (o resto funciona). Para
  forçar uma fonte específica: `VARVID_FONT=/caminho/para/fonte.ttf python local_app.py`.

Ao iniciar, o app imprime o status de cada um desses itens no terminal.

## Onde ficam os arquivos

Tudo é gravado em `./data/varvid/`. Para limpar, use o botão "Limpar" na interface
ou apague a pasta.

## Diferenças em relação à nuvem

- Não precisa dos tokens do Modal em `server.py` (removidos).
- O render usa os CPUs da sua máquina. Muitas variações em vídeos longos podem
  demorar — é normal.
- `engine.py`, `modal_app.py`, `server.py` e `build.sh` não são usados por esta
  versão (pode manter para referência).
