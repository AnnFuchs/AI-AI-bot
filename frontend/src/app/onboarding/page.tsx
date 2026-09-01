import Link from "next/link";

import { Button } from "@/shared/ui/button";
import { ArrowRightIcon } from "@/shared/ui/icons/arrow-right-icon";

const mascotImageSrc = "/images/ai-yai-mascot.png";

export default function OnboardingPage() {
  return (
    <main
      className="min-h-[100svh] w-full overflow-hidden bg-no-repeat lg:flex lg:items-center lg:justify-center"
      style={{
        backgroundImage: `url(${mascotImageSrc})`,
        backgroundPosition: "right bottom",
        backgroundSize: "clamp(220px, 92vw, 420px) auto",
      }}
    >
      <section className="mx-auto flex min-h-[100svh] max-w-4xl flex-col gap-5 px-4 pb-[clamp(17rem,114vw,32rem)] pt-6 min-[375px]:px-5 min-[375px]:pt-8 sm:px-8 sm:pt-8 lg:min-h-0 lg:max-w-xl lg:p-8">
        <p>
          Здравствуйте! Меня зовут Ай-Яй.
          <br />Я ваш помощник в жизни после инсульта.
        </p>
        <p>
          Я помогу разобраться в происходящем и сориентироваться в море информации о заболевании и
          жизни с ним. Также помогу не пропустить важные симптомы и чувствовать себя спокойнее и
          увереннее.
        </p>
        <p>Начнем с короткой настройки. Ответьте, пожалуйста, на вопросы.</p>

        <Button asChild className="w-fit max-w-full px-4">
          <Link href="/onboarding/questions">
            Ответить на вопросы
            <ArrowRightIcon aria-hidden="true" />
          </Link>
        </Button>
      </section>
    </main>
  );
}
