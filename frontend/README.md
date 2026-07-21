# AI Therapy Coach Frontend

Next.js frontend for the non-medical AI Therapy Coach prototype. The initial UI
provides a responsive landing/chat experience and calls the FastAPI conversation
endpoint. Login and registration protect the chat. Voice recording and avatar
rendering are visible placeholders only.

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
Authorization: Bearer <access_token>
```

Create an account at <http://localhost:3000/register>, or sign in at
<http://localhost:3000/login>. Registration signs in automatically and redirects
to the protected chat. Logging out removes the local token.

For this local MVP, only the JWT is stored under the versioned `localStorage`
key `therapy-coach:access-token:v1`. Production should prefer a
backend-for-frontend session with `HttpOnly`, `Secure`, `SameSite` cookies.

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
- `services/authService.ts`: registration, login, token storage, and `/auth/me`
- `app/login` and `app/register`: authentication pages
- `components/ProtectedChatPage.tsx`: local auth guard and logout
- `types/conversation.ts`: shared frontend request, response, and message types

This interface is not an emergency or medical service. It must not be presented
as a replacement for a qualified healthcare professional.
