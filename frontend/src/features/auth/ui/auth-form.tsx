"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";

import { ApiError } from "@/api/errors";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";

import { login, register } from "../api/auth-service";
import {
  formatPhoneInput,
  getCaretPositionForNationalDigitIndex,
  getMaskDigitRemovalIndex,
  getNationalDigitCaretIndex,
  isAllowedPhoneInput,
  isValidPhone,
  normalizePhone,
  PHONE_VALIDATION_MESSAGE,
  removeNationalDigitAt,
} from "../lib/phone-input";

type AuthFormProps = {
  mode: "login" | "register";
};

type AuthFormValues = {
  phone: string;
  password: string;
};

function isValidRegistrationPassword(password: string) {
  return /^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$/.test(password);
}

function getPasswordValidationMessage(mode: AuthFormProps["mode"]) {
  return mode === "register"
    ? "Пароль должен быть не короче 8 символов и содержать заглавную букву, строчную букву и цифру."
    : "Введите пароль.";
}

function getAuthErrorMessage(error: unknown, mode: AuthFormProps["mode"]) {
  if (mode === "login" && error instanceof ApiError && error.status === 401) {
    return "Неверный телефон или пароль.";
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Не получилось выполнить запрос. Попробуйте еще раз.";
}

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [apiError, setApiError] = useState<string | null>(null);
  const phoneInputRef = useRef<HTMLInputElement | null>(null);
  const form = useForm<AuthFormValues>({
    defaultValues: {
      phone: "",
      password: "",
    },
    reValidateMode: "onSubmit",
  });
  const phoneField = form.register("phone", {
    validate: (value) => isValidPhone(value) || PHONE_VALIDATION_MESSAGE,
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
    form.formState.errors.phone?.message ?? form.formState.errors.password?.message ?? apiError;

  const setPhoneValue = (value: string, nationalDigitCaretIndex: number) => {
    form.setValue("phone", value, {
      shouldDirty: true,
      shouldValidate: false,
    });
    form.clearErrors("phone");

    window.requestAnimationFrame(() => {
      const input = phoneInputRef.current;

      if (!input) {
        return;
      }

      const caretPosition = getCaretPositionForNationalDigitIndex(value, nationalDigitCaretIndex);
      input.setSelectionRange(caretPosition, caretPosition);
    });
  };

  const onSubmit = form.handleSubmit(async (values) => {
    setApiError(null);

    const phone = normalizePhone(values.phone);

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
      setApiError(getAuthErrorMessage(caughtError, mode));
    }
  });

  return (
    <form
      className="mx-auto flex w-full max-w-[300px] flex-col gap-5 min-[375px]:gap-6"
      onSubmit={onSubmit}
    >
      <div>
        <label htmlFor={`${mode}-login`} className="min-[375px]:text-xl min-[375px]:leading-6">
          Телефон
        </label>
        <Input
          className="mt-2 min-[375px]:text-xl min-[375px]:leading-6"
          autoComplete="tel"
          disabled={isSubmitting}
          id={`${mode}-login`}
          inputMode="tel"
          maxLength={18}
          aria-invalid={Boolean(form.formState.errors.phone)}
          {...phoneField}
          onKeyDown={(event) => {
            const input = event.currentTarget;
            const selectionStart = input.selectionStart ?? 0;
            const selectionEnd = input.selectionEnd ?? selectionStart;

            if (selectionStart !== selectionEnd) {
              return;
            }

            const digitIndexToRemove = getMaskDigitRemovalIndex(
              event.key,
              input.value,
              selectionStart,
            );

            if (digitIndexToRemove === null) {
              return;
            }

            event.preventDefault();
            setPhoneValue(
              removeNationalDigitAt(phoneValue, digitIndexToRemove),
              digitIndexToRemove,
            );
            setApiError(null);
          }}
          onBeforeInput={(event) => {
            const input = event.nativeEvent as InputEvent;

            if (input.data && !isAllowedPhoneInput(input.data)) {
              event.preventDefault();
            }
          }}
          onChange={(event) => {
            const input = event.currentTarget;

            setPhoneValue(
              formatPhoneInput(input.value),
              getNationalDigitCaretIndex(input.value, input.selectionStart ?? input.value.length),
            );
            setApiError(null);
          }}
          placeholder="+7 (999) 999-99-99"
          type="tel"
          value={phoneValue}
          ref={(element) => {
            phoneField.ref(element);
            phoneInputRef.current = element;
          }}
        />
      </div>

      <div>
        <label htmlFor={`${mode}-password`} className="min-[375px]:text-xl min-[375px]:leading-6">
          Пароль
        </label>
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
            form.clearErrors("password");
            setApiError(null);
          }}
        />
      </div>

      {formError ? (
        <p className="rounded-xl bg-destructive/10 px-4 py-3 text-destructive" role="alert">
          {formError}
        </p>
      ) : null}

      <Button disabled={isSubmitting} type="submit">
        {submitText}
      </Button>
    </form>
  );
}
