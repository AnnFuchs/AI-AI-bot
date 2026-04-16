"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/shared/ui/button";
import { Checkbox } from "@/shared/ui/checkbox";
import { Input } from "@/shared/ui/input";
import { RadioGroup, RadioGroupItem } from "@/shared/ui/radio-group";

const strokeTypeOptions = [
  { value: "ischemic", label: "Ишемический" },
  { value: "hemorrhagic", label: "Геморрагический" },
  { value: "unknown", label: "Не знаю" },
];

type DateFieldProps = {
  id: string;
  label: string;
  hint?: string;
  value: string;
  onChange: (value: string) => void;
};

export function OnboardingQuestionsForm() {
  const router = useRouter();
  const [strokeOwner, setStrokeOwner] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [sex, setSex] = useState("");
  const [strokeDate, setStrokeDate] = useState("");
  const [strokeTypes, setStrokeTypes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  function toggleStrokeType(value: string, checked: boolean) {
    setError(null);
    setStrokeTypes((current) => {
      if (checked) {
        return [...current, value];
      }

      return current.filter((item) => item !== value);
    });
  }

  return (
    <div className="flex min-h-full w-full max-w-sm flex-col">
      <form
        className="flex flex-1 flex-col gap-8"
        id="onboarding-questions-form"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();

          if (!strokeOwner || !birthDate || !sex || !strokeDate || strokeTypes.length === 0) {
            setError("Заполните, пожалуйста, все поля.");
            return;
          }

          router.push("/");
        }}
      >
        <fieldset>
          <RadioGroup
            className="flex flex-col gap-3"
            name="stroke-owner"
            onValueChange={(value) => {
              setStrokeOwner(value);
              setError(null);
            }}
            value={strokeOwner}
          >
            <label className="flex items-center gap-3 text-xl leading-6">
              <RadioGroupItem value="self" />
              У меня был инсульт
            </label>
            <label className="flex items-center gap-3 text-xl leading-6">
              <RadioGroupItem value="close-person" />
              У моего близкого был инсульт
            </label>
          </RadioGroup>
        </fieldset>

        <DateField
          id="birth-date"
          label="Дата рождения"
          onChange={(value) => {
            setBirthDate(value);
            setError(null);
          }}
          value={birthDate}
        />

        <fieldset>
          <legend className="mb-3 text-xl leading-6">Пол</legend>
          <RadioGroup
            className="flex flex-wrap gap-4"
            name="sex"
            onValueChange={(value) => {
              setSex(value);
              setError(null);
            }}
            value={sex}
          >
            <label className="flex items-center gap-3 text-xl leading-6">
              <RadioGroupItem value="male" />
              Муж
            </label>
            <label className="flex items-center gap-3 text-xl leading-6">
              <RadioGroupItem value="female" />
              Жен
            </label>
          </RadioGroup>
        </fieldset>

        <DateField
          hint="Если точная дата неизвестна, укажите примерную"
          id="stroke-date"
          label="Дата инсульта"
          onChange={(value) => {
            setStrokeDate(value);
            setError(null);
          }}
          value={strokeDate}
        />

        <fieldset>
          <legend className="mb-3 text-xl leading-6">Тип инсульта</legend>
          <div className="flex flex-col gap-3">
            {strokeTypeOptions.map((option) => (
              <label
                className="flex items-center gap-3 text-xl leading-6"
                key={option.value}
              >
                <Checkbox
                  checked={strokeTypes.includes(option.value)}
                  onCheckedChange={(checked) => {
                    toggleStrokeType(option.value, checked === true);
                  }}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        {error ? (
          <p className="text-lg leading-6 text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </form>

      <Button className="mt-8" form="onboarding-questions-form" type="submit">
        Готово
        <ArrowRightIcon aria-hidden="true" />
      </Button>
    </div>
  );
}

function DateField({ hint, id, label, onChange, value }: DateFieldProps) {
  return (
    <section className="flex flex-col gap-2">
      <label className="text-xl leading-6" htmlFor={id}>
        {label}
      </label>
      <Input
        autoComplete={id === "birth-date" ? "bday" : "off"}
        className="w-full max-w-[220px] text-xl"
        id={id}
        onChange={(event) => {
          onChange(event.currentTarget.value);
        }}
        type="date"
        value={value}
      />
      {hint ? (
        <p className="text-lg leading-6 text-muted-foreground">{hint}</p>
      ) : null}
    </section>
  );
}

function ArrowRightIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg fill="none" viewBox="0 0 32 32" {...props}>
      <path
        d="M6.66669 16H25.3334M25.3334 16L17.3334 8M25.3334 16L17.3334 24"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.5"
      />
    </svg>
  );
}
