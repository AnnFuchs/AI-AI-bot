import { apiClient } from "@/api/client";
import type { PushSubscriptionIn, ReminderOut, VapidPublicKeyOut } from "@/entities";

export function getVapidPublicKey() {
  return apiClient.request<VapidPublicKeyOut>("/reminders/vapid-public-key", {
    auth: false,
  });
}

export function savePushSubscription(subscription: PushSubscriptionIn) {
  return apiClient.request<Record<string, unknown>, PushSubscriptionIn>(
    "/reminders/push-subscription",
    {
      method: "POST",
      body: subscription,
    },
  );
}

export function deletePushSubscription(subscription: PushSubscriptionIn) {
  return apiClient.request<void, PushSubscriptionIn>("/reminders/push-subscription", {
    method: "DELETE",
    body: subscription,
  });
}

export function getReminders() {
  return apiClient.request<ReminderOut[]>("/reminders/");
}

export function deleteReminder(reminderId: string) {
  return apiClient.request<void>(`/reminders/${reminderId}`, {
    method: "DELETE",
  });
}
