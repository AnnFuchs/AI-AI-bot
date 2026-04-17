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

function isValidRegistrationPassword(password: string) {
  return /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$/.test(password);
}

function getPasswordValidationMessage(mode: AuthFormProps["mode"]) {
  return mode === "register"
    ? "Пароль должен быть не короче 8 символов и содержать заглавную букву, строчную букву и цифру."
    : "Введите пароль.";
}

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [apiError, setApiError] = useState<string | null>(null);
  const form = useForm<AuthFormValues>({
    defaultValues: {
      phone: "",
      password: "",
    },
  });
  const phoneField = form.register("phone", {
    validate: (value) =>
      Boolean(normalizePhoneForApi(value)) || "Введите номер телефона полностью.",
  });
  const passwordField = form.register("password", {
    validate: (value) => {
      if (!value) {
        return "Введите пароль.";
      }

      if (mode === "register" && !isValidRegistrationPassword(value)) {
        return getPasswordValidationMessage(mode);
      }

      return true;
    },
  });
  const phoneValue = form.watch("phone");
  const isSubmitting = form.formState.isSubmitting;
  const submitText = mode === "login" ? "Войти" : "Зарегистрироваться";
  const formError =
    form.formState.errors.phone?.message ??
    form.formState.errors.password?.message ??
    apiError;

  const onSubmit = form.handleSubmit(async (values) => {
    setApiError(null);

    const phone = normalizePhoneForApi(values.phone);

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

      router.push(mode === "register" ? "/onboarding" : "/");
    } catch (caughtError) {
      setApiError(
        caughtError instanceof Error
          ? caughtError.message
          : "Не получилось выполнить запрос. Попробуйте еще раз.",
      );
    }
  });

  return (
    <form
      className="mx-auto flex w-full max-w-[300px] flex-col gap-5 min-[375px]:gap-6"
      onSubmit={onSubmit}
    >
      <div>
        <label htmlFor={`${mode}-login`} className="min-[375px]:text-xl min-[375px]:leading-6">Телефон</label>
        <Input
            className="mt-2 min-[375px]:text-xl min-[375px]:leading-6"
            autoComplete="tel"
            disabled={isSubmitting}
            id={`${mode}-login`}
            inputMode="tel"
            maxLength={18}
            aria-invalid={Boolean(form.formState.errors.phone)}
            onChange={(event) => {
              form.setValue("phone", formatPhoneInput(event.currentTarget.value), {
                shouldDirty: true,
                shouldValidate: true,
              });
              setApiError(null);
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
        <label htmlFor={`${mode}-password`} className="min-[375px]:text-xl min-[375px]:leading-6">Пароль</label>
        <Input
            className="mt-2 min-[375px]:text-xl min-[375px]:leading-6"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            disabled={isSubmitting}
            id={`${mode}-password`}
            type="password"
            aria-invalid={Boolean(form.formState.errors.password)}
            {...passwordField}
            onChange={(event) => {
              passwordField.onChange(event);
              setApiError(null);
            }}
        />
      </div>

      {formError ? (
        <p
          className="rounded-xl bg-destructive/10 px-4 py-3 text-destructive"
          role="alert"
        >
          {formError}
        </p>
      ) : null}

      <Button disabled={isSubmitting} type="submit">
        {submitText}
      </Button>
    </form>
  );
}
