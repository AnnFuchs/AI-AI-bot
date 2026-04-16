import { AuthForm } from "@/features/auth/ui/auth-form";
import { Button } from "@/shared/ui/button";
import Link from "next/link";

export default function LoginPage() {
  return (
    <main className="flex min-h-dvh w-full flex-col items-center justify-center p-5">
      <AuthForm mode="login" />
      <div className="mt-12 flex w-full max-w-[300px] flex-col gap-4">
        <div className="h-px w-full bg-border" />
        <p className="text-center text-lg text-muted-foreground">
          Еще нет аккаунта?
        </p>
        <Button asChild className="w-full text-xl leading-6 text-muted-foreground" variant="outline">
          <Link href="/register">Зарегистрироваться</Link>
        </Button>
      </div>
    </main>
  );
}
