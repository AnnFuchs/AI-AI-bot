export type Alert = {
  id: string;
  title: string;
  severity: "info" | "warning" | "urgent";
  createdAt: string;
};
