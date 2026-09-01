export type Reminder = {
  id: string;
  title: string;
  dueAt: string;
  completed: boolean;
};

export type ReminderOut = {
  id: string;
  reminder_type: string;
  med_name: string | null;
  time: string | null;
  days: unknown[];
  is_active: boolean;
  created_at: string;
};

export type VapidPublicKeyOut = {
  public_key: string;
};

export type PushSubscriptionIn = {
  endpoint: string;
  p256dh: string;
  auth: string;
};
