export default function OfflinePage() {
  return (
    <main className="mx-auto flex min-h-[70vh] w-full max-w-2xl flex-col justify-center px-5 py-10">
      <p className="mb-3 text-sm font-semibold uppercase text-muted-foreground">
        Нет сети
      </p>
      <h1 className="text-3xl font-semibold leading-tight text-foreground">
        Сейчас вы не в сети.
      </h1>
      <p className="mt-4 text-lg leading-8 text-muted-foreground">
        Ай-Яю нужно подключение для чата и обновлений по уходу. Сохраненные
        страницы можно будет открыть здесь, когда стратегия кеширования PWA
        станет шире.
      </p>
    </main>
  );
}
