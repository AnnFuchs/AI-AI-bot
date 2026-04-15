import { PlaceholderPage } from "@/shared/layout/placeholder-page";

type ArticlePlaceholderPageProps = {
  params: Promise<{
    slug: string;
  }>;
};

const articleTitles: Record<string, string> = {
  "what-is-stroke": "Что такое инсульт?",
  "when-to-see-a-doctor": "Когда стоит обратиться к врачу?",
  "what-to-do-after-a-stroke": "Инсульт – что делать дальше?",
};

export default async function ArticlePlaceholderPage({
  params,
}: ArticlePlaceholderPageProps) {
  const { slug } = await params;

  return (
    <PlaceholderPage
      body="Статья пока не добавлена. Здесь будет материал из Базы знаний."
      eyebrow="База знаний"
      title={articleTitles[slug] ?? "Статья Базы знаний"}
    />
  );
}
