# CoBuilder

AI assistive tool for **house flippers and renovators**. Upload floorplan photos, screenshots, or image exports — CoBuilder uses **Microsoft Azure AI Foundry** to extract layout data, build a basic **3D visualization**, and help **plan renovations** with materials, tools, and cost estimates.

## What it does

1. **Floorplan analysis** — Vision model reads your image and returns structured room/wall/door data.
2. **3D preview** — Browser-based Three.js viewer extrudes rooms and walls from the AI output.
3. **Renovation planning** — Describe what you want to change; the agent estimates phases, materials, tools, and USD cost ranges.

## Azure setup (student account + $100 credit)

CoBuilder uses services covered by the [Azure for Students](https://azure.microsoft.com/en-us/free/students/) offer and your credit balance:

| Service | Use in CoBuilder | Cost tip |
|---------|------------------|----------|
| **Azure AI Foundry** | Prompt agent + vision model | Use `gpt-4o-mini` (cheap, vision-capable) |
| **Azure OpenAI / Foundry Models** | Floorplan OCR + renovation chat | Stay on mini/small models for dev |
| **Microsoft Entra ID** | `DefaultAzureCredential` / `az login` | Free |

### 1. Create Foundry resources

1. Sign in at [https://ai.azure.com](https://ai.azure.com) with your student account.
2. Create a **Foundry project** (or use an existing one).
3. Deploy a model — **`gpt-4o-mini`** is recommended for low cost with vision support.
4. Copy your **project endpoint** from the portal welcome screen:
   ```
   https://YOUR-RESOURCE.services.ai.azure.com/api/projects/YOUR-PROJECT
   ```

### 2. Authenticate locally

```powershell
az login
```

The app uses `DefaultAzureCredential`, which picks up your Azure CLI session. No API keys in code.

### 3. Configure CoBuilder

```powershell
cd C:\Users\Vrsm0\Projects\cobuilder
copy .env.example .env
```

Edit `.env`:

```env
FOUNDRY_PROJECT_ENDPOINT=https://YOUR-RESOURCE.services.ai.azure.com/api/projects/YOUR-PROJECT
FOUNDRY_AGENT_NAME=cobuilder-agent
FOUNDRY_MODEL=gpt-4o-mini
```

You can also open **Connection settings** in the app to change the Foundry
project endpoint/model separately from the Azure credential method. The default
uses `az login` through `DefaultAzureCredential`. For local development, the
optional service-principal mode accepts a tenant ID, client ID, and client
secret; the secret is saved only in the git-ignored `.env` file and is never
sent back to the browser. Do not use this local `.env` storage approach for a
deployed production app; use managed identity or a secret vault instead.

### 4. Run

```powershell
.\run.ps1
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Custom master prompt

Edit `backend/app/prompts/master_prompt.txt` to change CoBuilder's behavior (renovation style, cost assumptions, safety rules). The agent is re-created/updated on each server start.

## Project layout

```
cobuilder/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI routes
│   │   ├── config.py            # Settings from .env
│   │   ├── models.py            # Pydantic schemas
│   │   ├── prompts/
│   │   │   └── master_prompt.txt
│   │   └── services/
│   │       └── foundry_client.py  # Azure AI Foundry agent + vision
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── app.js               # Upload + API calls
│       └── viewer3d.js          # Three.js 3D viewer
├── .env.example
├── run.ps1
└── README.md
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/analyze-floorplan` | POST | Upload image → 3D scene JSON |
| `/api/plan-renovation` | POST | Scene JSON + request → renovation plan |
| `/api/chat` | POST | Free-form chat with CoBuilder agent |

## Notes

- Floorplan accuracy depends on image quality and labeled dimensions. Add hints in the upload form.
- Cost estimates are AI-generated ranges — verify with local suppliers and contractors.
- For structural, electrical, or plumbing work, always consult licensed professionals.
