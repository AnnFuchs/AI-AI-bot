type PlaceholderPageProps = {
  eyebrow: string;
  title: string;
  body: string;
};

export function PlaceholderPage({ eyebrow, title, body }: PlaceholderPageProps) {
  return (
    <main className="mx-auto w-full max-w-4xl px-5 py-8">
      <section className="max-w-2xl py-8">
        <p className="text-sm font-semibold uppercase leading-6 text-muted-foreground">
          {eyebrow}
        </p>
        <h1 className="mt-3 text-3xl font-semibold leading-6">{title}</h1>
        <p className="mt-4 text-muted-foreground">{body}</p>
      </section>
    </main>
  );
}
