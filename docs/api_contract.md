# Contrat API prévisionnel

Toutes les routes sont préfixées par `/api`. Les erreurs futures suivront un format stable `{code, message, details?, trace_id}`.

## `POST /api/conversation/message`

Entrée : `{ "message": "...", "session_id": "uuid optionnel" }`. Sortie : `{ "message": "...", "status": "pending|escalation_required" }`. Actuellement placeholder.

## `POST /api/documents/upload`

Multipart avec un champ `file` PDF. Réponse `202` : `{ "filename": "...", "status": "pending" }`. Validation et ingestion à implémenter.

## `POST /api/voice/transcribe`

Multipart avec `audio`. Retour futur : `{ "text": "...", "status": "completed" }`. Retourne actuellement `501` sans appel Whisper.

## `POST /api/voice/synthesize`

Entrée : `{ "text": "..." }`. Retour futur : `{ "audio_url": "...", "status": "completed" }`. Retourne actuellement `501` sans appel ElevenLabs.

## `GET /api/health`

Retour `200` : `{ "status": "ok" }`. Une future route de readiness vérifiera les dépendances séparément.
