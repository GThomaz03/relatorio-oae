# Como iniciar a aplicação

## Pré-requisitos

- Python 3.12+
- Node.js 20+
- npm

## 1) Instalar dependências

### Backend (Python)

```bash
cd d:\relatorio
pip install -e ".[dev]"
```

### Frontend (React)

```bash
cd d:\relatorio\frontend
npm install
```

## 2) Executar em desenvolvimento

Abra **2 terminais**.

### Terminal A - API FastAPI

```bash
cd d:\relatorio
python -m backend.api.server
```

API disponível em: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### Terminal B - Frontend Vite

```bash
cd d:\relatorio\frontend
npm run dev
```

Frontend disponível em: [http://127.0.0.1:5173](http://127.0.0.1:5173)

## 3) Build de produção (opcional)

### Frontend

```bash
cd d:\relatorio\frontend
npm run build
```

### Testes backend

```bash
cd d:\relatorio
python -m pytest backend/tests -q
```

## 4) Tela de gerenciamento

Com a aplicação aberta, use o menu lateral em **Gerenciamento** para:

- editar o catálogo YAML de templates de anomalias
- alterar template de título do relatório
- alterar template da linha de localização
- alterar template da legenda fotográfica

As configurações são persistidas no backend em `backend/rules/runtime_settings.json` e `backend/rules/descriptions.yaml`.
