import type { ConversationResponse } from "@/types/conversation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function sendMessage(message: string, sessionId?: string): Promise<ConversationResponse> {
  const response = await fetch(`${API_URL}/api/conversation/message`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!response.ok) throw new Error("Le service de conversation est indisponible.");
  return response.json() as Promise<ConversationResponse>;
}
