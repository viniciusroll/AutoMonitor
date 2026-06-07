# Vehicle Monitor

Sistema profissional em Python para **pesquisar, coletar, filtrar e monitorar
anúncios de veículos** em marketplaces online, com detecção de novos anúncios e
de redução de preço, alertas automáticos e exportação de relatórios.

Construído seguindo **SOLID** e **Clean Architecture**: cada fonte de dados é um
*provider* plugável e cada canal de alerta é desacoplado por interface, de modo
que novos sites ou canais possam ser adicionados sem alterar o restante do
sistema.

---

## Índice

- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Uso](#uso)
- [Exemplos](#exemplos)
- [Exportação](#exportação)
- [Alertas](#alertas)
- [Testes](#testes)
- [Troubleshooting](#troubleshooting)

---

## Arquitetura

O fluxo de dados segue camadas bem definidas:

```
CLI (Typer)
   │
   ▼
Services (orquestração: monitor, search, vehicle, stats)
   │            │                │
   ▼            ▼                ▼
Providers   Persistência    Notifications
(Playwright)  (SQLAlchemy)   (Telegram/Discord/Email)
```

Componentes principais:

| Camada | Pasta | Responsabilidade |
|--------|-------|------------------|
| **Providers** | `app/providers/` | Coleta nos marketplaces. `BaseVehicleProvider` define o contrato; `FacebookProvider` (Facebook Marketplace — **provider padrão**) e `WebmotorsProvider` são as implementações concretas. `BrowserManager` cuida de Playwright (scroll, retry, rotação de User-Agent). |
| **Models** | `app/models/` | Entidades ORM (`Vehicle`, `PriceHistory`, `Search`, `Notification`) e DTO `ScrapedVehicle` (Pydantic). |
| **Filters** | `app/filters/` | `VehicleFilter` — critérios configuráveis e serializáveis. |
| **Services** | `app/services/` | Casos de uso: dedup + histórico de preços, buscas salvas, orquestração e estatísticas. |
| **Notifications** | `app/notifications/` | `NotificationProvider` (interface) + canais + `NotificationDispatcher`. |
| **Exporters** | `app/exporters/` | `BaseExporter` + CSV / Excel / JSON. |
| **CLI** | `app/cli/` | Comandos Typer com saída Rich. |
| **Database** | `app/database/` | Engine, sessão e *migration* automática (`init_db`). |

**Decisões de design**

- *Open/Closed*: adicionar um novo site = criar uma subclasse de
  `BaseVehicleProvider` e registrá-la em `app/providers/registry.py`.
- Quando nenhuma fonte é especificada (`--source`), a busca usa os
  **providers padrão** — atualmente o **Facebook Marketplace**. O
  Webmotors continua registrado e disponível via `--source webmotors`.

> **⚠️ Facebook Marketplace exige login.** Todas as URLs de busca/categoria
> redirecionam para a página de login quando acessadas sem sessão. Por isso
> o fluxo usa uma **sessão autenticada persistida** (cookies via
> `storage_state` do Playwright): rode `python main.py login` **uma vez**,
> autentique-se na janela do navegador e a sessão salva em
> `auth/facebook_state.json` será reutilizada automaticamente. O diretório
> `auth/` é ignorado pelo git (contém credenciais de sessão).
- A coleta (`ScrapedVehicle`) é desacoplada da persistência (`Vehicle`).
- Seletores resilientes: cada campo tem uma **lista** de seletores
  alternativos; se o site mudar uma classe, basta acrescentar outra.
- Parsing defensivo: um anúncio malformado é ignorado sem derrubar a coleta.

### Banco de dados

SQLite criado automaticamente (`init_db` via `create_all`). Tabelas:
`vehicles`, `price_history`, `searches`, `notifications`. A unicidade lógica de
um anúncio é o par `(source, external_id)`, evitando duplicação; mudanças de
preço geram registro em `price_history`.

---

## Instalação

Requer **Python 3.12+**.

```bash
# 1. Clonar e entrar no diretório
cd vehicle_monitor

# 2. Criar e ativar o ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Instalar os navegadores do Playwright
playwright install chromium

# 5. Criar o arquivo de configuração
cp .env.example .env
```

---

## Configuração

Edite o `.env` (copiado de `.env.example`):

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DATABASE_URL` | `sqlite:///vehicle_monitor.db` | Conexão SQLAlchemy. |
| `HEADLESS` | `true` | `false` abre o navegador (depuração). |
| `MAX_RESULTS` | `100` | Máx. de anúncios por busca/provider. |
| `NAVIGATION_TIMEOUT` | `30000` | Timeout de navegação (ms). |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | — | Bot do Telegram. |
| `DISCORD_WEBHOOK` | — | URL do webhook do Discord. |
| `EMAIL_USER` / `EMAIL_PASSWORD` / `EMAIL_TO` | — | SMTP (envio de email). |
| `EMAIL_SMTP_HOST` / `EMAIL_SMTP_PORT` | `smtp.gmail.com` / `587` | Servidor SMTP. |
| `LOG_LEVEL` | `INFO` | `TRACE`…`CRITICAL`. |

Cada canal de alerta só é ativado quando suas variáveis estão preenchidas.

---

## Uso

```bash
# Inicializa/atualiza o schema do banco
python main.py db-init

# Login no Facebook (uma única vez) — o Marketplace exige autenticação.
# Abre o navegador; faça login e tecle ENTER no terminal. A sessão
# (cookies) é salva em auth/facebook_state.json e reutilizada nas buscas.
python main.py login

# Busca anúncios
python main.py search --brand "Honda" --model "Civic" --year-min 2018 --km-max 80000 --price-max 95000

# Lista providers disponíveis
python main.py providers

# Monitoramento contínuo das buscas salvas (a cada 30 min)
python main.py monitor --interval 30

# Exportação
python main.py export --format excel

# Estatísticas
python main.py stats

# Listar os anúncios salvos (com ID e link clicável)
python main.py list

# Abrir um anúncio no navegador (pelo ID que aparece no list/search)
python main.py open 1
python main.py open 1 --print   # apenas imprime a URL, sem abrir

# Ajuda de qualquer comando
python main.py search --help
```

### Opções de filtro do `search`

`--brand` `--model` `--version` `--year-min` `--year-max` `--km-max`
`--price-min` `--price-max` `--city` `--state` `--distance-max` `--fuel`
`--transmission` `--color` `--source` `--max` `--save <nome>` `--notify`

**Cidade, raio e preço no Facebook Marketplace:**

- `--city` define a **localização** da busca no Facebook (ex.: `--city "São Paulo"`
  → resultados da região de São Paulo). A busca abrange a **região
  metropolitana** da cidade — esse é, na prática, o "raio".
- `--price-min` / `--price-max` são enviados ao Facebook (`minPrice`/`maxPrice`),
  assim como `--year-min`/`--year-max` (`minYear`/`maxYear`) e `--km-max`
  (`maxMileage`).
- `--distance-max` (raio em km) é **aproximado**: o Facebook não aceita raio
  numérico via URL, então a distância é representada pela região da cidade
  escolhida. O valor é preservado nas buscas salvas e pode ser usado por
  outros providers no futuro.

---

## Exemplos

Buscar e **salvar** a busca para monitoramento posterior:

```bash
python main.py search \
  --brand "Honda" --model "Civic" \
  --year-min 2018 --km-max 80000 --price-max 95000 \
  --state SP --save "civic-sp" --notify
```

Monitorar **apenas** a busca salva, uma única vez:

```bash
python main.py monitor --name "civic-sp" --once
```

Exportar somente anúncios de uma fonte:

```bash
python main.py export --format json --source webmotors --output ./exports/webmotors.json
```

---

## Exportação

Formatos suportados: **CSV** (UTF-8 com BOM, abre direto no Excel), **Excel**
(`.xlsx` formatado, cabeçalho fixo) e **JSON** (indentado). Os arquivos são
gravados em `exports/` com *timestamp*, salvo se `--output` for informado.

---

## Alertas

O `NotificationDispatcher` envia por **todos os canais habilitados** quando:

- 🆕 um novo anúncio é encontrado;
- 📉 há redução de preço;
- 🎯 um veículo entra nos critérios.

Cada envio é registrado na tabela `notifications` (auditoria). Para adicionar um
canal novo, implemente `NotificationProvider` e inclua-o em
`app/notifications/dispatcher.py`.

---

## Testes

```bash
# Suíte completa
pytest

# Com relatório de cobertura
pytest --cov --cov-report=term-missing
```

A suíte cobre filtros, parsing, providers, persistência (dedup + histórico),
detecção de queda de preço, exportadores, notificações e orquestração — com
**cobertura acima de 80%** da lógica de negócio (bordas de I/O — Playwright,
SMTP/HTTP e CLI — são validadas por integração manual).

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| `playwright._impl...Executable doesn't exist` | Rode `playwright install chromium`. |
| `make_metavar() missing ... 'ctx'` (Typer) | Use `click<8.2` (já fixado em `requirements.txt`). |
| Navegador não abre / fica travado | Defina `HEADLESS=false` no `.env` para depurar visualmente. |
| Facebook redireciona para `/login` e coleta 0 anúncios | O Marketplace exige sessão autenticada. Rode `python main.py login` uma vez para salvar os cookies; as buscas seguintes reutilizam essa sessão. |
| Sessão do Facebook expirou | Rode `python main.py login` novamente para regenerar `auth/facebook_state.json`. |
| Nenhum anúncio coletado | O layout do site pode ter mudado; ajuste os seletores em `app/providers/facebook.py` ou `app/providers/webmotors.py` (listas de alternativas / seletores estáveis). |
| Timeouts frequentes | Aumente `NAVIGATION_TIMEOUT` no `.env`. |
| Alertas não chegam | Confirme as variáveis do canal no `.env`; rode `python main.py stats` para ver notificações registradas. |
| Banco "travado" (`database is locked`) | Evite execuções simultâneas sobre o mesmo arquivo SQLite. |

---

## Estrutura do projeto

```
vehicle_monitor/
├── app/
│   ├── providers/      # coleta (Playwright) — base, browser, facebook, webmotors, registry
│   ├── database/       # engine, sessão, init_db
│   ├── models/         # ORM + DTO + enums
│   ├── services/       # casos de uso (monitor, search, vehicle, stats)
│   ├── notifications/  # canais desacoplados + dispatcher
│   ├── exporters/      # CSV / Excel / JSON
│   ├── filters/        # VehicleFilter
│   ├── cli/            # comandos Typer
│   ├── utils/          # logger, parsing
│   ├── config.py       # settings (.env via Pydantic)
│   └── exceptions.py   # hierarquia de erros
├── tests/              # pytest (cobertura 85%)
├── logs/               # logs/app.log (rotativo)
├── exports/            # arquivos exportados
├── .env.example
├── requirements.txt
├── pytest.ini
└── main.py             # entrypoint da CLI
```
