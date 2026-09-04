# App SPPB — Avaliação de Idosos com Dashboard

Aplicação Streamlit para fisioterapeutas aplicarem o teste **Short
Physical Performance Battery (SPPB)**, com cálculo automático do
escore, armazenamento no Google Sheets e dashboard de acompanhamento.

## Estrutura do projeto

```
sppb_app/
├── app.py              # Interface Streamlit (formulário + dashboard)
├── sppb_score.py        # Lógica de pontuação (testada, independente da UI)
├── sheets_utils.py       # Integração com Google Sheets
└── requirements.txt
```

## Passo a passo de configuração (fazer uma única vez)

### 1. Criar a planilha no Google Sheets
Crie uma planilha nova (pode estar vazia). Copie o ID dela a partir
da URL:
```
https://docs.google.com/spreadsheets/d/ESTE_TRECHO_AQUI/edit
```

### 2. Criar a Service Account no Google Cloud
1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Crie um projeto (ou use um existente)
3. Ative as APIs: **Google Sheets API** e **Google Drive API**
4. Vá em "IAM e administrador" → "Contas de serviço" → "Criar conta de serviço"
5. Após criada, gere uma **chave** em formato **JSON** e baixe o arquivo
6. Copie o e-mail da service account (formato `algo@projeto.iam.gserviceaccount.com`)

### 3. Compartilhar a planilha com a Service Account
Na planilha do Google Sheets, clique em "Compartilhar" e adicione o
e-mail da service account com permissão de **Editor**.

### 4. Configurar os secrets no Streamlit

**Localmente**, crie o arquivo `.streamlit/secrets.toml` (não o suba
para o Git — adicione ao `.gitignore`):

```toml
sheet_id = "ID_DA_SUA_PLANILHA"

[gcp_service_account]
type = "service_account"
project_id = "seu-projeto"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "algo@seu-projeto.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Todos esses campos vêm diretamente do arquivo JSON baixado no passo 2
— copie os valores correspondentes.

**No Streamlit Community Cloud**, cole o mesmo conteúdo em
Settings → Secrets (interface web), não é necessário arquivo local.

## Executando localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicando (Streamlit Community Cloud, gratuito)

1. Suba o projeto para um repositório no GitHub (sem o `secrets.toml`)
2. Acesse [share.streamlit.io](https://share.streamlit.io)
3. Conecte o repositório e aponte para `app.py`
4. Configure os secrets na interface do Streamlit Cloud (passo 4 acima)
5. A URL gerada é a "página host" que os fisioterapeutas vão acessar

## Regras de pontuação implementadas

A lógica em `sppb_score.py` segue o protocolo oficial (Guralnik et al.),
incluindo as regras de **interrupção antecipada**:
- Se falhar no teste de pés juntos → equilíbrio encerra em 0 pontos
- Se falhar no semi-tandem → equilíbrio encerra no que já tinha (1 ponto)
- Se não conseguir o pré-teste de sentar-levantar sem os braços → força = 0 pontos

Os pontos de corte de risco de mortalidade exibidos no app são baseados em:
- **Escore <10**: associado a maior mortalidade por todas as causas (achado
  consistente na maioria dos 40 estudos revisados)
- **Escore <5**: único ponto de corte formalmente validado (sensibilidade
  0,66; especificidade 0,62), derivado de idosos pós-alta hospitalar
  (Corsonello et al., 2012) — não necessariamente generalizável a outros
  contextos clínicos (ex.: comunidade, ambulatório)

## Próximos passos sugeridos
- [ ] Adicionar autenticação simples (login por fisioterapeuta)
- [ ] Campo de motivo de não realização do teste (7 códigos do protocolo)
- [ ] Exportar relatório individual em PDF
- [ ] Filtro por setor/unidade no dashboard
