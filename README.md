# OAE Report Generator

Aplicativo **desktop Windows** (Electron + FastAPI) para geração automatizada de relatórios técnicos de inspeção OAE.

## Pré-requisitos

- Python 3.12+
- Node.js 20+
- Windows 10/11

## Instalação

```powershell
cd d:\relatorio
pip install -e ".[dev]"
npm install
cd frontend
npm install
cd ..
```

## Desenvolvimento

Inicia backend desktop, frontend Vite e Electron:

```powershell
npm run desktop:dev
```

Documentação detalhada: [TUTORIAL_DESKTOP.md](TUTORIAL_DESKTOP.md)

## Build e distribuição

```powershell
npm run desktop:build   # frontend + PyInstaller + Electron
npm run desktop:dist    # instalador NSIS / portable
```

## Testes

```powershell
python -m pytest backend/tests -q
npm run desktop:smoke
```

## Estrutura

| Pasta | Descrição |
|-------|-----------|
| `backend/` | API FastAPI, pipeline DOCX, regras YAML |
| `frontend/` | Interface React (renderer Electron) |
| `electron/` | Processo principal, IPC, gestão do backend |
| `scripts/` | Build e smoke tests desktop |
| `pyinstaller/` | Spec do backend empacotado |

## Dados do usuário

Em produção, workspaces e configurações editáveis ficam em:

`%APPDATA%\OAE Report Generator\data\`

## Documentação

- [TUTORIAL_DESKTOP.md](TUTORIAL_DESKTOP.md) — desenvolvimento, build e troubleshooting
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — contexto de negócio
- [SPECIFICATION.md](SPECIFICATION.md) — especificação técnica
- [backend/templates/PLACEHOLDERS.md](backend/templates/PLACEHOLDERS.md) — placeholders do template Word
