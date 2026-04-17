"use client";

import Link from "next/link";
import {usePathname, useRouter} from "next/navigation";
import {useEffect, useState} from "react";

import {getAccessToken} from "@/features/auth/lib/token-storage";
import {cn} from "@/shared/lib/utils";
import {BookIcon} from "@/shared/ui/icons/book-icon";
import {ChatIcon} from "@/shared/ui/icons/chat-icon";
import {SettingsIcon} from "@/shared/ui/icons/settings-icon";
import {Button} from "@/shared/ui/button";

const navItems = [
    {href: "/", label: "Чат", Icon: ChatIcon},
    {href: "/learn", label: "База знаний", Icon: BookIcon},
    {href: "/settings", label: "Настройки", Icon: SettingsIcon},
];

export function AppShell({children}: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [isAuthReady, setIsAuthReady] = useState(false);
    const isChatPage = pathname === "/";
    const isPublicAuthPage =
        pathname === "/login" ||
        pathname === "/register";
    const shouldHideNavigation =
        isPublicAuthPage ||
        pathname.startsWith("/onboarding");

    useEffect(() => {
        setIsAuthReady(false);

        const hasAccessToken = Boolean(getAccessToken());

        if (!hasAccessToken && !isPublicAuthPage) {
            router.replace("/login");
            return;
        }

        if (hasAccessToken && isPublicAuthPage) {
            router.replace("/");
            return;
        }

        setIsAuthReady(true);
    }, [isPublicAuthPage, pathname, router]);

    if (!isAuthReady) {
        return <div className="min-h-dvh bg-background" />;
    }

    return (
        <div className="min-h-dvh bg-background text-foreground">
            {!shouldHideNavigation ? (
                <header className={cn(
                    "sticky top-0 z-20 bg-background p-1.5 min-[375px]:p-2",
                    !isChatPage &&
                    "after:pointer-events-none after:absolute after:inset-x-0 after:top-full after:h-3 after:bg-gradient-to-b after:from-background after:to-transparent",
                )}>
                    <nav aria-label="Разделы приложения" className="mx-auto w-full max-w-4xl">
                        <ul className="flex min-h-14 w-full items-center gap-1.5 min-[375px]:min-h-16 min-[375px]:gap-2">
                            {navItems.map((item) => {
                                const isActive =
                                    item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                                const Icon = item.Icon;

                                return (
                                    <li className="flex-1" key={item.href}>
                                        <Button asChild variant="ghost" className={cn(
                                            "h-14 w-full [&_svg]:size-8 min-[375px]:h-16",
                                            isActive && "bg-muted text-foreground",
                                        )}>
                                            <Link
                                                aria-current={isActive ? "page" : undefined}
                                                aria-label={item.label}
                                                href={item.href}
                                                title={item.label}
                                            >
                                                <Icon aria-hidden="true" className="size-8"/>
                                            </Link>
                                        </Button>
                                    </li>
                                );
                            })}
                        </ul>
                    </nav>
                </header>
            ) : null}
            {children}
        </div>
    );
}
