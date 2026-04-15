type PlaceholderPageProps = {
  eyebrow: string;
  title: string;
  body: string;
};

export function PlaceholderPage({ eyebrow, title, body }: PlaceholderPageProps) {
  return (
    <main className="mx-auto w-full max-w-4xl px-5 py-8">
      <section className="max-w-2xl py-8">
        <p className="text-sm font-semibold uppercase text-muted-foreground">
          {eyebrow}
        </p>
        <h1 className="mt-3 text-3xl font-semibold leading-tight">{title}</h1>
        <p className="mt-4 text-lg leading-8 text-muted-foreground">{body}</p>
      </section>
    </main>
  );
}
