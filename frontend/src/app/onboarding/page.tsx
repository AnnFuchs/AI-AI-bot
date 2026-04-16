import Link from "next/link";

import { Button } from "@/shared/ui/button";

export default function OnboardingPage() {
  return (
    <main className="flex flex-col gap-5 min-h-dvh max-w-4xl p-8">
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

      <Button asChild className="w-fit">
        <Link href="/settings">
          Ответить на вопросы
          <ArrowRightIcon aria-hidden="true" />
        </Link>
      </Button>
    </main>
  );
}

function ArrowRightIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" viewBox="0 0 32 32" {...props}>
      <path
        d="M6.66669 16H25.3334M25.3334 16L17.3334 8M25.3334 16L17.3334 24"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.5"
      />
    </svg>
  );
}
