"use client";

import { useCallback, useEffect, useState } from "react";

import { USE_MOCK_API } from "@/api/config";
import type { PushSubscriptionIn } from "@/entities";

import {
  deletePushSubscription,
  getVapidPublicKey,
  savePushSubscription,
} from "../api/notifications-service";

type PushSupportState = {
  isSupported: boolean;
  reason?: string;
};

const PUSH_OPERATION_TIMEOUT_MS = 15_000;
const mockSubscription: PushSubscriptionIn = {
  auth: "mock-auth",
  endpoint: "https://mock.push.local/subscription",
  p256dh: "mock-p256dh",
};

function getPushSupportState(): PushSupportState {
  if (typeof window === "undefined") {
    return {
      isSupported: false,
      reason: "Уведомления доступны только в браузере.",
    };
  }

  if (!window.isSecureContext) {
    return {
      isSupported: false,
      reason: "Уведомления работают только на HTTPS, localhost или 127.0.0.1.",
    };
  }

  if (!("Notification" in window)) {
    return {
      isSupported: false,
      reason: "Этот браузер не поддерживает уведомления.",
    };
  }

  if (!("serviceWorker" in navigator)) {
    return {
      isSupported: false,
      reason: "Этот браузер не поддерживает Service Worker.",
    };
  }

  if (!("PushManager" in window)) {
    return {
      isSupported: false,
      reason: "Этот браузер не поддерживает push-уведомления.",
    };
  }

  return { isSupported: true };
}

function withTimeout<T>(promise: Promise<T>, message: string) {
  return new Promise<T>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      reject(new Error(message));
    }, PUSH_OPERATION_TIMEOUT_MS);

    promise
      .then(resolve)
      .catch(reject)
      .finally(() => {
        window.clearTimeout(timeout);
      });
  });
}

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = `${base64String}${padding}`.replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let index = 0; index < rawData.length; index += 1) {
    outputArray[index] = rawData.charCodeAt(index);
  }

  return outputArray;
}

function arrayBufferToBase64(buffer: ArrayBuffer | null) {
  if (!buffer) {
    return "";
  }

  const bytes = new Uint8Array(buffer);
  let binary = "";

  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }

  return window.btoa(binary);
}

function toPushSubscriptionIn(subscription: PushSubscription): PushSubscriptionIn {
  return {
    endpoint: subscription.endpoint,
    p256dh: arrayBufferToBase64(subscription.getKey("p256dh")),
    auth: arrayBufferToBase64(subscription.getKey("auth")),
  };
}

async function registerServiceWorker() {
  const registration = await navigator.serviceWorker.getRegistration("/");

  if (registration) {
    return registration;
  }

  await navigator.serviceWorker.register("/sw.js");

  return withTimeout(
    navigator.serviceWorker.ready,
    "Service Worker не активировался. Обновите страницу и попробуйте еще раз.",
  );
}

export function usePushSubscription() {
  const [supportState, setSupportState] = useState<PushSupportState>(() => getPushSupportState());
  const [permission, setPermission] = useState<NotificationPermission>("default");
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshSubscriptionState = useCallback(async () => {
    const nextSupportState = getPushSupportState();
    setSupportState(nextSupportState);
    setError(null);

    if (!nextSupportState.isSupported) {
      setIsSubscribed(false);
      setIsLoading(false);
      return;
    }

    setPermission(Notification.permission);

    if (USE_MOCK_API) {
      setIsSubscribed(false);
      setIsLoading(false);
      return;
    }

    try {
      const registration = await navigator.serviceWorker.getRegistration("/");
      const subscription = await registration?.pushManager.getSubscription();
      setIsSubscribed(Boolean(subscription));
    } catch {
      setIsSubscribed(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshSubscriptionState();
  }, [refreshSubscriptionState]);

  const enable = useCallback(async () => {
    const nextSupportState = getPushSupportState();
    setSupportState(nextSupportState);
    setError(null);

    if (!nextSupportState.isSupported) {
      setError(nextSupportState.reason ?? "Push-уведомления недоступны.");
      return false;
    }

    setIsLoading(true);

    try {
      let nextPermission = Notification.permission;

      if (nextPermission === "default") {
        nextPermission = await Notification.requestPermission();
      }

      setPermission(nextPermission);

      if (nextPermission !== "granted") {
        setError("Разрешение на уведомления не выдано в браузере.");
        setIsSubscribed(false);
        return false;
      }

      const registration = await registerServiceWorker();

      if (USE_MOCK_API) {
        await savePushSubscription(mockSubscription);
        setIsSubscribed(true);
        return true;
      }

      const currentSubscription = await registration.pushManager.getSubscription();
      const subscription =
        currentSubscription ??
        (await withTimeout(
          registration.pushManager.subscribe({
            applicationServerKey: urlBase64ToUint8Array((await getVapidPublicKey()).public_key),
            userVisibleOnly: true,
          }),
          "Браузер слишком долго создавал push-подписку. Проверьте доступ к push-сервисам Chrome.",
        ));

      await savePushSubscription(toPushSubscriptionIn(subscription));
      setIsSubscribed(true);

      return true;
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Не получилось включить push-уведомления.",
      );
      setIsSubscribed(false);

      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const disable = useCallback(async () => {
    const nextSupportState = getPushSupportState();
    setSupportState(nextSupportState);
    setError(null);

    if (!nextSupportState.isSupported) {
      setIsSubscribed(false);
      return true;
    }

    setIsLoading(true);

    try {
      const registration = await navigator.serviceWorker.getRegistration("/");
      const subscription = await registration?.pushManager.getSubscription();

      if (USE_MOCK_API && !subscription) {
        await deletePushSubscription(mockSubscription);
        setIsSubscribed(false);
        return true;
      }

      if (subscription) {
        await deletePushSubscription(toPushSubscriptionIn(subscription));
        await subscription.unsubscribe();
      }

      setIsSubscribed(false);

      return true;
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Не получилось отключить push-уведомления.",
      );

      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    disable,
    enable,
    error,
    isLoading,
    isSubscribed,
    isSupported: supportState.isSupported,
    permission,
    refreshSubscriptionState,
    supportReason: supportState.reason,
  };
}
