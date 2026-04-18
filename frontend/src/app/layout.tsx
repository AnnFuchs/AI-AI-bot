import type { Metadata, Viewport } from "next";

import { AppShell } from "@/shared/layout/app-shell";
import { ServiceWorkerRegistration } from "@/shared/pwa/service-worker-registration";

import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Ай-Яй - Инсультный Бадди",
    template: "%s | Ай-Яй - Инсультный Бадди",
  },
  description:
    "Ежедневная поддержка во время восстановления после инсульта.",
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  themeColor: "#486F49",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
          <ServiceWorkerRegistration />
        </Providers>
      </body>
    </html>
  );
}
