"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";

import {cn} from "@/shared/lib/utils";
import {BookIcon} from "@/shared/ui/icons/book-icon";
import {ChatIcon} from "@/shared/ui/icons/chat-icon";
import {SettingsIcon} from "@/shared/ui/icons/settings-icon";

const navItems = [
    {href: "/", label: "Чат", Icon: ChatIcon},
    {href: "/learn", label: "База знаний", Icon: BookIcon},
    {href: "/settings", label: "Настройки", Icon: SettingsIcon},
];

export function AppShell({children}: { children: React.ReactNode }) {
    const pathname = usePathname();

    return (
        <div className="min-h-dvh bg-background text-foreground">
            <header className="sticky bg-background top-0 z-20 p-2">
                <nav aria-label="Разделы приложения" className="mx-auto w-full max-w-4xl">
                    <ul className="flex min-h-16 w-full items-center gap-2">
                        {navItems.map((item) => {
                            const isActive =
                                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                            const Icon = item.Icon;

                            return (
                                <li className="flex-1" key={item.href}>
                                    <Link
                                        aria-current={isActive ? "page" : undefined}
                                        aria-label={item.label}
                                        className={cn(
                                            "flex min-h-12 w-full min-w-12 items-center justify-center rounded-xl p-4 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
                                            isActive && "bg-muted text-foreground",
                                        )}
                                        href={item.href}
                                        title={item.label}
                                    >
                                        <Icon aria-hidden="true" className="size-8"/>
                                    </Link>
                                </li>
                            );
                        })}
                    </ul>
                </nav>
            </header>
            {children}
        </div>
    );
}