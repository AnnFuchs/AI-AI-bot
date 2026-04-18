import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/shared/lib/utils";

function isExternalHref(href?: string) {
  return Boolean(href?.startsWith("http://") || href?.startsWith("https://"));
}

type MarkdownMessageProps = {
  children: string;
  className?: string;
};

export function MarkdownMessage({ children, className }: MarkdownMessageProps) {
  return (
    <div className={cn("space-y-3 break-words", className)}>
      <ReactMarkdown
        components={{
          a: ({ children, href }) => {
            if (!href) {
              return <>{children}</>;
            }

            if (isExternalHref(href)) {
              return (
                <a className="underline" href={href} rel="noreferrer" target="_blank">
                  {children}
                </a>
              );
            }

            return (
              <Link className="underline" href={href}>
                {children}
              </Link>
            );
          },
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-border pl-3 text-muted-foreground">
              {children}
            </blockquote>
          ),
          code: ({ children, className }) => {
            const isInline = !className;

            if (isInline) {
              return <code className="rounded bg-muted px-1">{children}</code>;
            }

            return (
              <code
                className={cn(
                  "block overflow-x-auto whitespace-pre-wrap rounded bg-muted p-3",
                  className,
                )}
              >
                {children}
              </code>
            );
          },
          h1: ({ children }) => <p className="font-semibold">{children}</p>,
          h2: ({ children }) => <p className="font-semibold">{children}</p>,
          h3: ({ children }) => <p className="font-semibold">{children}</p>,
          li: ({ children }) => <li className="break-words">{children}</li>,
          ol: ({ children }) => <ol className="list-decimal space-y-2 pl-6">{children}</ol>,
          p: ({ children }) => <p className="whitespace-pre-wrap">{children}</p>,
          pre: ({ children }) => <pre>{children}</pre>,
          ul: ({ children }) => <ul className="list-disc space-y-2 pl-6">{children}</ul>,
        }}
        remarkPlugins={[remarkGfm]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
