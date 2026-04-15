export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
};

export type ChatRequest = {
  message: string;
  conversationId?: string;
  profileId?: string;
};

export type SSEEvent =
  | {
      type: "token";
      token: string;
    }
  | {
      type: "done";
      conversationId?: string;
    }
  | {
      type: "error";
      message: string;
    }
  | {
      type: "metadata";
      data: Record<string, unknown>;
    };
