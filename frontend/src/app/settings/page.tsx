"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { logout } from "@/features/auth/api/auth-service";
import { clearAuthToken, getRefreshToken } from "@/features/auth/lib/token-storage";
import { Button } from "@/shared/ui/button";

export default function SettingsPage() {
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

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

  return (
    <main className="mx-auto w-full max-w-4xl px-4 pb-8 pt-3 min-[375px]:px-5">
      <section className="max-w-2xl">
        <p className="text-sm font-semibold uppercase leading-6 text-muted-foreground">Настройки</p>
        <h1 className="mt-3 text-3xl font-semibold leading-6">Настройте Ай-Яй под себя.</h1>
        <p className="mt-4">Здесь появятся настройки профиля, доступности и важных контактов.</p>
        <Button
          className="mt-8"
          disabled={isLoggingOut}
          onClick={handleLogout}
          type="button"
          variant="outline"
        >
          Выйти
        </Button>
      </section>
    </main>
  );
}
