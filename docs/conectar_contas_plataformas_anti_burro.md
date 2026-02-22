# Conectar Contas das Plataformas (Anti-Burro)

Objetivo: deixar as contas conectadas no Social Agent para ficar pronto para deploy.

Arquivo de segredos usado pelo projeto: `ops/cloudrun/secrets.env`

## 1. Preparar arquivo de credenciais

```bash
cp ops/cloudrun/secrets.env.example ops/cloudrun/secrets.env
```

## 2. Reddit (perfil Reddit do agente)

1. Entrar em `https://www.reddit.com/prefs/apps`.
2. Criar app do tipo `script`.
3. Definir um `redirect uri` (pode ser `http://localhost:8080`, apenas obrigatorio de cadastro).
4. Copiar:
   - client id
   - client secret
5. Usar a conta do bot (username/password dedicados).
6. Preencher em `ops/cloudrun/secrets.env`:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USERNAME`
   - `REDDIT_PASSWORD`

Observacao tecnica: o conector usa password flow (`grant_type=password`), por isso precisa usuario e senha.

## 3. X/Twitter (obrigatorio na estrategia, sem API paga via modo operator)

1. Definir o modo sem custo no runtime:
   - Em `ops/cloudrun/deploy.env`: `X_EXECUTION_MODE=operator`
2. Gerar um token interno forte para ingestao no webhook X:
   - Exemplo: `openssl rand -hex 32`
3. Preencher em `ops/cloudrun/secrets.env`:
   - `X_WEBHOOK_TOKEN` (obrigatorio para proteger `/webhooks/x`)
4. Credenciais `X_API_*` e `X_ACCESS_*` ficam opcionais nesse modo.

Observacao tecnica: em `operator`, o agente continua planejando e decidindo no X, mas a execucao vai para fila operacional (`/ops/operator/tasks`) sem usar API paga.

## 4. Meta (Facebook + Instagram)

1. Entrar em Meta for Developers e criar um App.
2. Conectar uma Facebook Page.
3. Conectar uma conta Instagram Professional ligada a essa Page.
4. Capturar:
   - `META_APP_SECRET` (Settings > Basic)
   - `META_PAGE_ACCESS_TOKEN` (token da pagina)
   - `META_IG_USER_ID` (ID da conta IG profissional)
   - `META_VERIFY_TOKEN` (valor que voce define)
5. Preencher em `ops/cloudrun/secrets.env` com os valores acima.

Permissoes minimas praticas para operar post/reply/webhook:
- `pages_manage_posts`
- `pages_read_engagement`
- `pages_manage_metadata`
- `instagram_basic`
- `instagram_content_publish`
- `instagram_manage_comments`

## 4.1 Operacao do Instagram no agente

Para publicar proativamente no Instagram, configure tambem em `ops/cloudrun/deploy.env`:
- `INSTAGRAM_DEFAULT_IMAGE_URL` com URL publica de imagem (`https://...`).

Sem `INSTAGRAM_DEFAULT_IMAGE_URL`, o agente pula publish proativo no Instagram para evitar erro da API.

Opcoes gratis para hospedar a imagem:
- Cloud Storage publico (bucket de assets).
- GitHub raw de um asset estatico.
- CDN gratuita de imagem.

## 5. Subir segredos para o GCP

```bash
./ops/cloudrun/sync_secrets.sh ops/cloudrun/deploy.env ops/cloudrun/secrets.env
```

Isso cria/atualiza os segredos no Secret Manager e vincula acesso para a service account do runtime.

## 6. Validar se todas as contas foram conectadas

```bash
./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
```

Para validar tambem o E2E live do LLM:

```bash
RUN_LIVE_LLM_E2E=1 ./ops/cloudrun/predeploy_check.sh ops/cloudrun/deploy.env
```

## 7. Registrar webhook do Meta (depois do deploy)

Depois que tiver URL do Cloud Run:

- Callback URL: `https://<service-url>/webhooks/meta`
- Verify token: o mesmo valor de `META_VERIFY_TOKEN`

Teste rapido:

```bash
curl -sS "https://<service-url>/webhooks/meta?hub.mode=subscribe&hub.verify_token=<META_VERIFY_TOKEN>&hub.challenge=12345"
```

Resultado esperado: retorno `12345`.

## 7.1 Integrar ingestao de sinais do X (depois do deploy)

Usar endpoint:
- `POST https://<service-url>/webhooks/x`
- Header: `X-Social-Agent-Token: <X_WEBHOOK_TOKEN>`

Teste rapido:

```bash
curl -sS -X POST "https://<service-url>/webhooks/x" \
  -H "content-type: application/json" \
  -H "x-social-agent-token: <X_WEBHOOK_TOKEN>" \
  -d '{"tweet_id":"tw_123","text":"teste de mencao no x"}'
```

Resultado esperado: `status=accepted`.

## 8. Segurança para nao confundir com outro servico

Em `ops/cloudrun/deploy.env`:
- `PROJECT_ID=vertice-ai-42`
- `SERVICE_NAME` com nome exclusivo deste social-agent (nao usar nome do agente Twitch)
- `ALLOW_UPDATE_EXISTING_SERVICE=0` enquanto estiver preparando
