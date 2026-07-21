import type {
  ConversationRequest,
  ConversationResponse,
} from "@/types/conversation";
import { getAccessToken, logout } from "@/services/authService";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Send one conversation turn to the backend delivery API. */
export async function sendMessage(
  request: ConversationRequest,
  signal?: AbortSignal,
): Promise<ConversationResponse> {
  let response: Response;
  const accessToken = getAccessToken();
  if (!accessToken) {
    throw new ApiError("Please sign in before starting a conversation.", 401);
  }

  try {
    response = await fetch(`${API_URL}/api/conversation/message`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify(request),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(
      "The backend could not be reached. Check that it is running on port 8000.",
    );
  }

  if (!response.ok) {
    if (response.status === 401) {
      logout();
      window.location.assign("/login");
    }
    throw new ApiError(
      "The conversation service could not process your message.",
      response.status,
    );
  }

  return (await response.json()) as ConversationResponse;
}
