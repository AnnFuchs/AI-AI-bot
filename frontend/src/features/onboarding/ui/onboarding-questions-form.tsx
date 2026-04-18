"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/shared/ui/button";
import { ArrowRightIcon } from "@/shared/ui/icons/arrow-right-icon";
import { Input } from "@/shared/ui/input";
import { RadioGroup, RadioGroupItem } from "@/shared/ui/radio-group";
import type { Role, Sex, StrokeType } from "@/entities";

import { updateCurrentUser } from "../api/user-service";

const strokeTypeOptions = [
  { value: "ischemic", label: "Ишемический" },
  { value: "hemorrhagic", label: "Геморрагический" },
  { value: "unknown", label: "Не знаю" },
];

function getRoleFromStrokeOwner(strokeOwner: string): Role {
  return strokeOwner === "close-person" ? "relative" : "patient";
}

type DateFieldProps = {
  id: string;
  label: string;
  hint?: string;
  disabled?: boolean;
  value: string;
  onChange: (value: string) => void;
};

export function OnboardingQuestionsForm() {
  const router = useRouter();
  const [strokeOwner, setStrokeOwner] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [sex, setSex] = useState("");
  const [strokeDate, setStrokeDate] = useState("");
  const [strokeType, setStrokeType] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  return (
    <div className="flex min-h-[calc(100svh-3rem)] w-full max-w-sm flex-col min-[375px]:min-h-[calc(100svh-4rem)]">
      <form
        className="flex flex-1 flex-col gap-5 min-[375px]:gap-6"
        id="onboarding-questions-form"
        noValidate
        onSubmit={async (event) => {
          event.preventDefault();

          if (!strokeOwner || !birthDate || !sex || !strokeDate || !strokeType) {
            setError("Пожалуйста, заполните все поля.");
            return;
          }

          setError(null);
          setIsSubmitting(true);

          try {
            await updateCurrentUser({
              date_of_birth: birthDate,
              role: getRoleFromStrokeOwner(strokeOwner),
              sex: sex as Sex,
              stroke_date: strokeDate,
              stroke_type: strokeType as StrokeType,
            });

            router.push("/");
          } catch (caughtError) {
            setError(
              caughtError instanceof Error
                ? caughtError.message
                : "Не получилось сохранить данные. Попробуйте еще раз.",
            );
          } finally {
            setIsSubmitting(false);
          }
        }}
      >
        <fieldset>
          <legend className="mb-2 min-[375px]:text-xl min-[375px]:leading-6">
            У кого был инсульт?
          </legend>
          <RadioGroup
            className="flex flex-col gap-3"
            disabled={isSubmitting}
            name="stroke-owner"
            onValueChange={(value) => {
              setStrokeOwner(value);
              setError(null);
            }}
            value={strokeOwner}
          >
            <label className="flex min-w-0 cursor-pointer items-center gap-3 min-[375px]:text-xl min-[375px]:leading-6">
              <RadioGroupItem value="self" />
              <span className="min-w-0">У меня</span>
            </label>
            <label className="flex min-w-0 cursor-pointer items-center gap-3 min-[375px]:text-xl min-[375px]:leading-6">
              <RadioGroupItem value="close-person" />
              <span className="min-w-0">У моего близкого</span>
            </label>
          </RadioGroup>
        </fieldset>

        <DateField
          hint="Укажите дату рождения человека, перенесшего инсульт"
          id="birth-date"
          label="Дата рождения"
          disabled={isSubmitting}
          onChange={(value) => {
            setBirthDate(value);
            setError(null);
          }}
          value={birthDate}
        />

        <fieldset>
          <legend className="mb-2 min-[375px]:text-xl min-[375px]:leading-6">Пол</legend>
          <RadioGroup
            className="flex flex-wrap gap-4"
            disabled={isSubmitting}
            name="sex"
            onValueChange={(value) => {
              setSex(value);
              setError(null);
            }}
            value={sex}
          >
            <label className="flex cursor-pointer items-center gap-3 min-[375px]:text-xl min-[375px]:leading-6">
              <RadioGroupItem value="male" />
              Муж
            </label>
            <label className="flex cursor-pointer items-center gap-3 min-[375px]:text-xl min-[375px]:leading-6">
              <RadioGroupItem value="female" />
              Жен
            </label>
          </RadioGroup>
        </fieldset>

        <DateField
          hint="Если точная дата неизвестна, укажите примерную"
          id="stroke-date"
          label="Дата инсульта"
          disabled={isSubmitting}
          onChange={(value) => {
            setStrokeDate(value);
            setError(null);
          }}
          value={strokeDate}
        />

        <fieldset>
          <legend className="mb-2 min-[375px]:text-xl min-[375px]:leading-6">Тип инсульта</legend>
          <RadioGroup
            className="flex flex-col gap-3"
            disabled={isSubmitting}
            name="stroke-type"
            onValueChange={(value) => {
              setStrokeType(value);
              setError(null);
            }}
            value={strokeType}
          >
            {strokeTypeOptions.map((option) => (
              <label
                className="flex min-w-0 cursor-pointer items-center gap-3 min-[375px]:text-xl min-[375px]:leading-6"
                key={option.value}
              >
                <RadioGroupItem value={option.value} />
                <span className="min-w-0">{option.label}</span>
              </label>
            ))}
          </RadioGroup>
        </fieldset>

        {error ? (
          <p className="rounded-xl bg-destructive/10 px-4 py-3 text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </form>

      <Button
        className="mt-8 w-full"
        disabled={isSubmitting}
        form="onboarding-questions-form"
        type="submit"
      >
        Готово
        <ArrowRightIcon aria-hidden="true" />
      </Button>
    </div>
  );
}

function DateField({ disabled, hint, id, label, onChange, value }: DateFieldProps) {
  return (
    <section className="flex flex-col gap-2">
      <label className="min-[375px]:text-xl min-[375px]:leading-6" htmlFor={id}>
        {label}
      </label>
      <Input
        autoComplete={id === "birth-date" ? "bday" : "off"}
        className="w-full max-w-[220px] min-[375px]:text-xl min-[375px]:leading-6"
        disabled={disabled}
        id={id}
        onChange={(event) => {
          onChange(event.currentTarget.value);
        }}
        type="date"
        value={value}
      />
      {hint ? (
        <p className="max-w-[280px] text-base leading-6 text-muted-foreground min-[375px]:text-lg min-[375px]:leading-6">
          {hint}
        </p>
      ) : null}
    </section>
  );
}
