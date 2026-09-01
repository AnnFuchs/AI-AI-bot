import Link from "next/link";

import { learnArticles } from "@/features/learn/lib/articles";
import { Button } from "@/shared/ui/button";

const articleGroups = [
  {
    title: "Об инсульте",
    slugs: ["what-is-stroke", "why-stroke-happens", "is-stroke-treatable"],
  },
  {
    title: "Лечение и профилактика",
    slugs: [
      "why-so-many-pills",
      "do-pills-harm-liver",
      "can-you-get-addicted-to-pills",
      "why-take-pressure-and-cholesterol-pills",
      "can-stroke-happen-again",
      "how-to-clean-blood-vessels",
    ],
  },
  {
    title: "Жизнь после инсульта",
    slugs: [
      "can-you-fly-after-stroke",
      "can-you-drink-alcohol-after-stroke",
      "can-you-have-sex-after-stroke",
    ],
  },
];

function getArticlesBySlugs(slugs: string[]) {
  return slugs
    .map((slug) => learnArticles.find((article) => article.slug === slug))
    .filter((article) => article !== undefined);
}

export default function LearnPage() {
  return (
    <main className="mx-auto w-full max-w-4xl px-4 pb-8 pt-3 min-[375px]:px-5">
      <div className="pb-5">
        <p className="text-sm font-semibold uppercase leading-6 text-muted-foreground">
          База знаний
        </p>
        <h1 className="mt-3 text-3xl font-semibold leading-7">Полезная информация рядом.</h1>
        <p className="mt-4 max-w-2xl">
          Короткие ответы на частые вопросы о заболевании, восстановлении и жизни после инсульта.
        </p>
      </div>

      <div className="flex flex-col gap-5">
        {articleGroups.map((group, index) => {
          return (
            <section
              className="border-t border-border pt-5"
              key={group.title}
            >
              <h2 className="mb-3 text-muted-foreground">{group.title}</h2>
              <div className="flex flex-col items-start gap-2">
                {getArticlesBySlugs(group.slugs).map((article) => (
                  <Button
                    asChild
                    className="min-h-12 h-auto max-w-full justify-start whitespace-normal text-left"
                    key={article.slug}
                    variant="chat"
                  >
                    <Link href={`/learn/articles/${article.slug}`}>{article.title}</Link>
                  </Button>
                ))}
              </div>
            </section>
          );
        })}
      </div>
    </main>
  );
}
