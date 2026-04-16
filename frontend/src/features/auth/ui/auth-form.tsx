"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";

import { login, register } from "../api/auth-service";

type AuthFormProps = {
  mode: "login" | "register";
};

type AuthFormValues = {
  phone: string;
  password: string;
};

function getPhoneDigits(value: string) {
  const digits = value.replace(/\D/g, "");

  if (!digits) {
    return "";
  }

  if (digits.startsWith("8")) {
    return `7${digits.slice(1)}`.slice(0, 11);
  }

  if (digits.startsWith("7")) {
    return digits.slice(0, 11);
  }

  return `7${digits}`.slice(0, 11);
}

function formatPhoneInput(value: string) {
  const digits = getPhoneDigits(value);

  if (!digits) {
    return "";
  }

  const nationalNumber = digits.slice(1);
  const parts = ["+7"];

  if (nationalNumber.length > 0) {
    parts.push(` (${nationalNumber.slice(0, 3)}`);
  }

  if (nationalNumber.length >= 3) {
    parts[1] = `${parts[1]})`;
  }

  if (nationalNumber.length > 3) {
    parts.push(` ${nationalNumber.slice(3, 6)}`);
  }

  if (nationalNumber.length > 6) {
    parts.push(`-${nationalNumber.slice(6, 8)}`);
  }

  if (nationalNumber.length > 8) {
    parts.push(`-${nationalNumber.slice(8, 10)}`);
  }

  return parts.join("");
}

function normalizePhoneForApi(value: string) {
  const digits = getPhoneDigits(value);

  return digits.length === 11 ? `+${digits}` : "";
}

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const form = useForm<AuthFormValues>({
    defaultValues: {
      phone: "",
      password: "",
    },
  });
  const phoneField = form.register("phone", { required: true });
  const phoneValue = form.watch("phone");
  const isSubmitting = form.formState.isSubmitting;
  const submitText = mode === "login" ? "Войти" : "Зарегистрироваться";

  const onSubmit = form.handleSubmit(async (values) => {
    setError(null);

    const phone = normalizePhoneForApi(values.phone);

    if (!phone) {
      setError("Введите номер телефона полностью.");
      return;
    }

    try {
      if (mode === "login") {
        await login({
          login: phone,
          password: values.password,
        });
      } else {
        await register({
          phone,
          password: values.password,
        });
      }

      router.push("/");
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Не получилось выполнить запрос. Попробуйте еще раз.",
      );
    }
  });

  return (
    <form className="max-w-[300px] w-full mx-auto flex flex-col gap-6" onSubmit={onSubmit}>
      <div>
        <label htmlFor={`${mode}-login`} className="text-xl">Телефон</label>
        <Input
            className="mt-2 text-xl"
            autoComplete="tel"
            disabled={isSubmitting}
            id={`${mode}-login`}
            inputMode="tel"
            maxLength={18}
            onChange={(event) => {
              form.setValue("phone", formatPhoneInput(event.currentTarget.value), {
                shouldDirty: true,
                shouldValidate: true,
              });
            }}
            placeholder="+7 (999) 999-99-99"
            type="tel"
            value={phoneValue}
            name={phoneField.name}
            onBlur={phoneField.onBlur}
            ref={phoneField.ref}
        />
      </div>

      <div>
        <label htmlFor={`${mode}-password`} className="text-xl">Пароль</label>
        <Input
            className="mt-2 text-xl"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            disabled={isSubmitting}
            id={`${mode}-password`}
            type="password"
            {...form.register("password", { required: true })}
        />
      </div>

      {error ? <p role="alert">{error}</p> : null}

      <Button disabled={isSubmitting} type="submit" className="text-xl leading-6">
        {submitText}
      </Button>
    </form>
  );
}
