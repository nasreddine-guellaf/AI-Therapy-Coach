# AI Therapy Coach Frontend

Next.js frontend for the non-medical AI Therapy Coach prototype. The initial UI
provides a responsive landing/chat experience and calls the FastAPI conversation
endpoint. Voice recording and avatar rendering are visible placeholders only.

## Requirements

- Node.js 20+
- npm
- The backend running on `http://localhost:8000`

## Configure

Create `frontend/.env.local` when the backend uses a different URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Do not place private API keys in `NEXT_PUBLIC_*` variables because these values
are included in browser code.

## Run locally

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. The chat sends:

```http
POST http://localhost:8000/api/conversation/message
Content-Type: application/json
```

The browser must be allowed by the backend CORS configuration. The backend
currently permits `http://localhost:3000` by default.

## Validation

```powershell
npm run typecheck
npm run build
```

## Structure

- `components/ChatInterface.tsx`: chat state and user interaction
- `components/MessageBubble.tsx`: message presentation
- `components/VoiceRecorder.tsx`: disabled voice placeholder
- `components/AvatarPanel.tsx`: avatar/status placeholder
- `services/apiClient.ts`: all HTTP communication with FastAPI
- `types/conversation.ts`: shared frontend request, response, and message types

This interface is not an emergency or medical service. It must not be presented
as a replacement for a qualified healthcare professional.
