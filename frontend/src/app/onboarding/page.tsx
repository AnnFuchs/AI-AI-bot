import Link from "next/link";

import { Button } from "@/shared/ui/button";
import { ArrowRightIcon } from "@/shared/ui/icons/arrow-right-icon";

export default function OnboardingPage() {
  return (
    <main className="flex min-h-[100svh] max-w-4xl flex-col gap-5 px-4 py-6 min-[375px]:px-5 min-[375px]:py-8 sm:p-8">
        <p className="text-lg leading-6">
          Здравствуйте! Меня зовут Ай-Яй.
          <br />Я ваш помощник в жизни после инсульта.
        </p>
        <p className="text-lg leading-6">
          Я помогу разобраться в происходящем и сориентироваться в море
          информации о заболевании и жизни с ним. Также помогу не пропустить
          важные симптомы и чувствовать себя спокойнее и увереннее.
        </p>
        <p className="text-lg leading-6">
          Начнем с короткой настройки. Ответьте, пожалуйста, на вопросы
        </p>

      <Button asChild className="h-10 max-w-full px-4 text-base min-[375px]:h-12 min-[375px]:text-lg">
        <Link href="/onboarding/questions">
          Ответить на вопросы
          <ArrowRightIcon aria-hidden="true" />
        </Link>
      </Button>
    </main>
  );
}
