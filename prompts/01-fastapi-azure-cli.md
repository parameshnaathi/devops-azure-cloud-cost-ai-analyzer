\# Prompt 1: FastAPI Backend + Azure CLI



Create a Python FastAPI backend in a `backend/` folder for the AI Cloud Cost Detective project.



\## What to build



\- A FastAPI server with a `POST /api/analyze` endpoint that accepts `{ "resource\_group": "<name>" }`.

\- A `GET /api/resource-groups` endpoint that returns the list of Azure resource groups.

\- Use Python's `subprocess` module to run Azure CLI commands:

&#x20; - `az group list` to list all resource groups.

&#x20; - `az resource list --resource-group <name> -o json` to fetch all resources in the selected group.

\- Parse the Azure CLI JSON output and return a structured response with resource type, name, location, SKU, and tags.

\- Add error handling for Azure CLI not installed, not logged in, or invalid resource group.

\- Enable CORS for `http://localhost:5173`.

\- Include a `requirements.txt` with `fastapi`, `uvicorn`.



\## Project structure



```

backend/

├── main.py

├── azure\_scanner.py

├── requirements.txt

```



Refer to `Architecture.MD` and `RequestFlow.MD`. This covers step ③ of the request flow.

