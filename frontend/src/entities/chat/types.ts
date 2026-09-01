export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
  actions?: ChatAction[];
  alerts?: ChatAlert[];
  sources?: ChatSources[];
};

export type ChatAction = {
  id: string;
  label: string;
  href: string;
};

export type ChatRedFlag = {
  name: string;
  level: string;
  description: string;
  target_info?: string;
};

export type ChatAlert = {
  message: string;
  red_flags: ChatRedFlag[];
};

export type ChatSource = {
  source: string;
  title?: string;
  url?: string;
};

export type ChatSources = {
  confidence?: number;
  confidence_label?: string;
  sources: ChatSource[];
  used_rag?: boolean;
};

export type ChatRequest = {
  session_id: string;
  message: string;
};

export type SSEEvent =
  | {
      type: "token";
      token: string;
    }
  | {
      type: "text";
      text: string;
    }
  | {
      type: "button";
      button: Omit<ChatAction, "id">;
    }
  | {
      type: "alert";
      alert: ChatAlert;
    }
  | {
      type: "sources";
      sources: ChatSources;
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
