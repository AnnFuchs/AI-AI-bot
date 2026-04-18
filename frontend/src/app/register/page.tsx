import { AuthForm } from "@/features/auth/ui/auth-form";
import { Button } from "@/shared/ui/button";
import Link from "next/link";

export default function RegisterPage() {
  return (
    <main className="flex min-h-[100svh] w-full flex-col items-center justify-center px-4 py-6 min-[375px]:p-5">
      <AuthForm mode="register" />
      <div className="mt-10 flex w-full max-w-[300px] flex-col gap-3 min-[375px]:mt-12 min-[375px]:gap-4">
        <div className="h-px w-full bg-border" />
        <p className="text-center text-muted-foreground">
          Уже зарегистрированы?
        </p>
        <Button asChild className="w-full text-muted-foreground" variant="outline">
          <Link href="/login">Войти</Link>
        </Button>
      </div>
    </main>
  );
}
