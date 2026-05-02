"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, BellOff, Loader2, LogOut, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { logout } from "@/features/auth/api/auth-service";
import { clearAuthToken, getRefreshToken } from "@/features/auth/lib/token-storage";
import { deleteReminder, getReminders } from "@/features/notifications/api/notifications-service";
import { usePushSubscription } from "@/features/notifications/hooks/use-push-subscription";
import {
  getCurrentUser,
  syncTimezone,
  updateCurrentUser,
} from "@/features/onboarding/api/user-service";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";

const userQueryKey = ["current-user"] as const;
const remindersQueryKey = ["reminders"] as const;

const fallbackTimezones = [
  { value: "Europe/Kaliningrad", label: "Калининград (UTC+2)" },
  { value: "Europe/Moscow", label: "Москва, Санкт-Петербург (UTC+3)" },
  { value: "Europe/Samara", label: "Самара, Удмуртия (UTC+4)" },
  { value: "Asia/Yekaterinburg", label: "Екатеринбург (UTC+5)" },
  { value: "Asia/Novosibirsk", label: "Новосибирск, Омск (UTC+7)" },
  { value: "Asia/Krasnoyarsk", label: "Красноярск (UTC+7)" },
  { value: "Asia/Irkutsk", label: "Иркутск (UTC+8)" },
  { value: "Asia/Yakutsk", label: "Якутск (UTC+9)" },
  { value: "Asia/Vladivostok", label: "Владивосток (UTC+10)" },
  { value: "Asia/Kamchatka", label: "Камчатка, Чукотка (UTC+12)" },
  { value: "UTC", label: "UTC (UTC+0)" },
];

export default function SettingsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const pushSubscription = usePushSubscription();
  const detectedTimezone =
    typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "UTC";

  const timezoneOptions = useMemo(() => {
    const isAlreadyInList = fallbackTimezones.some(({ value }) => value === detectedTimezone);

    return isAlreadyInList
      ? fallbackTimezones
      : [{ value: detectedTimezone, label: detectedTimezone }, ...fallbackTimezones];
  }, [detectedTimezone]);

  const userQuery = useQuery({
    queryKey: userQueryKey,
    queryFn: getCurrentUser,
  });

  const remindersQuery = useQuery({
    queryKey: remindersQueryKey,
    queryFn: getReminders,
  });

  const dailyCheckinMutation = useMutation({
    mutationFn: (daily_checkin_enabled: boolean) =>
      updateCurrentUser({
        daily_checkin_enabled,
      }),
    onSuccess: (user) => {
      queryClient.setQueryData(userQueryKey, user);
    },
  });

  const timezoneMutation = useMutation({
    mutationFn: (timezone: string) => syncTimezone({ timezone }),
    onSuccess: (user) => {
      queryClient.setQueryData(userQueryKey, user);
    },
  });

  const deleteReminderMutation = useMutation({
    mutationFn: deleteReminder,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: remindersQueryKey });
    },
  });

  async function handleLogout() {
    const refreshToken = getRefreshToken();

    setIsLoggingOut(true);

    try {
      if (refreshToken) {
        await logout(refreshToken);
      }
    } finally {
      clearAuthToken();
      router.replace("/login");
      router.refresh();
    }
  }

  const user = userQuery.data;
  const dailyCheckinEnabled = user?.daily_checkin_enabled ?? true;
  const selectedTimezone = user?.timezone ?? detectedTimezone;
  const reminders = remindersQuery.data ?? [];

  return (
    <main className="mx-auto w-full max-w-4xl px-4 pb-8 pt-3 min-[375px]:px-5">
      <div className="pb-5">
        <p className="text-sm font-semibold uppercase leading-6 text-muted-foreground">Настройки</p>
        <h1 className="mt-3 text-3xl font-semibold leading-7">Настройте Ай-Яй под себя.</h1>
        <p className="mt-4 max-w-2xl">
          Здесь вы можете настроить уведомления и другие полезные функции.
        </p>
      </div>

      <div className="flex flex-col gap-5">
        <section className="border-t border-border pt-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold">Push-уведомления</h2>
              <p className="mt-2 max-w-xl text-muted-foreground">
                Напоминания будут приходить, даже если вкладка закрыта.
              </p>
              {!pushSubscription.isSupported ? (
                <p className="mt-3 text-sm text-destructive">{pushSubscription.supportReason}</p>
              ) : null}
              {pushSubscription.error ? (
                <p className="mt-3 text-sm text-destructive">{pushSubscription.error}</p>
              ) : null}
            </div>

            <SwitchButton
              checked={pushSubscription.isSubscribed}
              disabled={!pushSubscription.isSupported || pushSubscription.isLoading}
              icon={
                pushSubscription.isLoading ? (
                  <Loader2 aria-hidden="true" className="animate-spin" />
                ) : pushSubscription.isSubscribed ? (
                  <Bell aria-hidden="true" />
                ) : (
                  <BellOff aria-hidden="true" />
                )
              }
              label={pushSubscription.isSubscribed ? "Выключить" : "Включить"}
              onChange={async (checked) => {
                if (checked) {
                  await pushSubscription.enable();
                  return;
                }

                await pushSubscription.disable();
              }}
            />
          </div>
        </section>

        <section className="border-t border-border pt-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-xl font-semibold">Дневник самочувствия</h2>
              <p className="mt-2 max-w-xl text-muted-foreground">
                Ай-Яй будет напоминать о ежедневной отметке самочувствия.
              </p>
              {dailyCheckinMutation.error ? (
                <p className="mt-3 text-sm text-destructive">
                  Не получилось сохранить настройку. Попробуйте еще раз.
                </p>
              ) : null}
            </div>

            <SwitchButton
              checked={dailyCheckinEnabled}
              disabled={userQuery.isLoading || dailyCheckinMutation.isPending}
              label={dailyCheckinEnabled ? "Выключить" : "Включить"}
              onChange={(checked) => {
                dailyCheckinMutation.mutate(checked);
              }}
            />
          </div>
        </section>

        <section className="border-t border-border pt-5">
          <label className="block text-xl font-semibold" htmlFor="timezone">
            Часовой пояс
          </label>
          <p className="mt-2 max-w-xl text-muted-foreground">
            Используется для расписания напоминаний.
          </p>
          <Select
            disabled={userQuery.isLoading || timezoneMutation.isPending}
            onValueChange={(value) => {
              timezoneMutation.mutate(value);
            }}
            value={selectedTimezone}
          >
            <SelectTrigger className="mt-4 max-w-sm" id="timezone">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {timezoneOptions.map(({ value, label }) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {timezoneMutation.error ? (
            <p className="mt-3 text-sm text-destructive">Не получилось сохранить часовой пояс.</p>
          ) : null}
        </section>

        <section className="border-t border-border pt-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-xl font-semibold">Активные напоминания</h2>
              <p className="mt-2 max-w-xl text-muted-foreground">
                Здесь показаны все ваши активные напоминания.
              </p>
            </div>
            {remindersQuery.isFetching ? (
              <Loader2
                aria-hidden="true"
                className="mt-1 size-5 animate-spin text-muted-foreground"
              />
            ) : null}
          </div>

          <div className="mt-5 flex flex-col gap-3">
            {remindersQuery.isError ? (
              <p className="text-sm text-destructive">Не получилось загрузить напоминания.</p>
            ) : null}
            {!remindersQuery.isLoading && reminders.length === 0 ? (
              <p className="text-muted-foreground">Активных напоминаний пока нет.</p>
            ) : null}
            {reminders.map((reminder) => (
              <div
                className="flex items-center justify-between gap-4 rounded-lg border-2 border-border bg-white px-4 py-3"
                key={reminder.id}
              >
                <div className="min-w-0">
                  <p className="font-medium leading-6">{formatReminderTitle(reminder)}</p>
                  <p className="text-sm text-muted-foreground">{formatReminderMeta(reminder)}</p>
                </div>
                <Button
                  aria-label="Удалить напоминание"
                  disabled={deleteReminderMutation.isPending}
                  onClick={() => {
                    deleteReminderMutation.mutate(reminder.id);
                  }}
                  size="icon"
                  type="button"
                  variant="ghost"
                >
                  <Trash2 aria-hidden="true" />
                </Button>
              </div>
            ))}
          </div>
        </section>

        <div className="border-t border-border pt-5">
          <Button disabled={isLoggingOut} onClick={handleLogout} type="button" variant="outline">
            {isLoggingOut ? (
              <Loader2 aria-hidden="true" className="animate-spin" />
            ) : (
              <LogOut aria-hidden="true" />
            )}
            Выйти
          </Button>
        </div>
      </div>
    </main>
  );
}

type SwitchButtonProps = {
  checked: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  label: string;
  onChange: (checked: boolean) => void | Promise<void>;
};

function SwitchButton({ checked, disabled, icon, label, onChange }: SwitchButtonProps) {
  return (
    <Button
      aria-checked={checked}
      className={cn(
        "w-full justify-between sm:w-48",
        checked && "border-primary bg-primary text-primary-foreground hover:bg-primary",
      )}
      disabled={disabled}
      onClick={() => {
        void onChange(!checked);
      }}
      role="switch"
      variant="outline"
    >
      <span className="min-w-0 truncate">{label}</span>
      <span className="shrink-0">{icon}</span>
    </Button>
  );
}

type ReminderDisplay = {
  reminder_type: string;
  med_name: string | null;
  time: string | null;
  days: unknown[];
};

function formatReminderTitle(reminder: ReminderDisplay) {
  if (reminder.med_name) {
    return reminder.med_name;
  }

  if (reminder.reminder_type === "daily_checkin") {
    return "Ежедневная отметка самочувствия";
  }

  return "Напоминание";
}

function formatReminderMeta(reminder: ReminderDisplay) {
  const parts: string[] = [];

  if (reminder.time) {
    parts.push(reminder.time.slice(0, 5));
  }

  if (reminder.days.length > 0) {
    parts.push(reminder.days.map(String).join(", "));
  }

  if (parts.length === 0) {
    return "Без расписания";
  }

  return parts.join(" · ");
}
