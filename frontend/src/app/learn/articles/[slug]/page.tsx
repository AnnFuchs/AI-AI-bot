import Link from "next/link";
import { notFound } from "next/navigation";

import { getLearnArticle, learnArticles } from "@/features/learn/lib/articles";
import { Button } from "@/shared/ui/button";
import { ArrowLeftIcon } from "@/shared/ui/icons/arrow-left-icon";

type ArticlePageProps = {
  params: Promise<{
    slug: string;
  }>;
};

export function generateStaticParams() {
  return learnArticles.map((article) => ({
    slug: article.slug,
  }));
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const { slug } = await params;
  const article = getLearnArticle(slug);

  if (!article) {
    notFound();
  }

  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-3 min-[375px]:px-5">
      <Button
        asChild
        className="w-fit max-w-full px-4"
        variant="outline"
      >
        <Link href="/learn">
          <ArrowLeftIcon aria-hidden="true" />
          Ко всем статьям
        </Link>
      </Button>

      <article className="pb-5 pt-5">
        <p className="text-sm font-semibold uppercase leading-6 text-muted-foreground">
          База знаний
        </p>
        <h1 className="mt-3 text-3xl font-semibold leading-6">
          {article.title}
        </h1>
        <div className="mt-6 space-y-4">
          {article.body.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
      </article>
    </main>
  );
}
