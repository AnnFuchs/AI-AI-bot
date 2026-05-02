export const PHONE_VALIDATION_MESSAGE = "Введите номер в формате +79999999999 или 89999999999.";

const PHONE_MAX_NATIONAL_DIGITS = 10;

function getDigits(value: string) {
  return value.replace(/\D/g, "");
}

export function formatPhoneInput(value: string) {
  const allowedChars = value.replace(/[^\d+]/g, "");

  if (!allowedChars) {
    return "";
  }

  if (allowedChars.startsWith("+")) {
    if (allowedChars.length === 1) {
      return "+";
    }

    if (!allowedChars.startsWith("+7")) {
      return "+";
    }

    return formatPhoneParts("+7", allowedChars.slice(2));
  }

  if (allowedChars.startsWith("8")) {
    return formatPhoneParts("8", allowedChars.slice(1));
  }

  return "";
}

function formatPhoneParts(prefix: "+7" | "8", nationalDigits: string) {
  const digits = getDigits(nationalDigits).slice(0, PHONE_MAX_NATIONAL_DIGITS);

  if (!digits) {
    return prefix;
  }

  const areaCode = digits.slice(0, 3);
  const firstPart = digits.slice(3, 6);
  const secondPart = digits.slice(6, 8);
  const thirdPart = digits.slice(8, 10);
  const parts = [prefix, ` (${areaCode}`];

  if (areaCode.length === 3) {
    parts[1] = `${parts[1]})`;
  }

  if (firstPart) {
    parts.push(` ${firstPart}`);
  }

  if (secondPart) {
    parts.push(`-${secondPart}`);
  }

  if (thirdPart) {
    parts.push(`-${thirdPart}`);
  }

  return parts.join("");
}

export function isValidPhone(value: string) {
  return Boolean(normalizePhone(value));
}

export function normalizePhone(value: string) {
  const phone = value.trim();
  const digits = getDigits(phone);

  if (phone.startsWith("+") && /^7\d{10}$/.test(digits)) {
    return `+${digits}`;
  }

  if (/^8\d{10}$/.test(digits)) {
    return `+7${digits.slice(1)}`;
  }

  return "";
}

export function isAllowedPhoneInput(value: string) {
  return /^[+\d\s()-]+$/.test(value);
}

function getNationalDigits(value: string) {
  const phone = value.trim();
  const digits = getDigits(phone);

  if (phone.startsWith("+") && digits.startsWith("7")) {
    return digits.slice(1, PHONE_MAX_NATIONAL_DIGITS + 1);
  }

  if (digits.startsWith("8")) {
    return digits.slice(1, PHONE_MAX_NATIONAL_DIGITS + 1);
  }

  return "";
}

export function getNationalDigitCaretIndex(value: string, caretPosition: number) {
  const digitsBeforeCaret = getDigits(value.slice(0, caretPosition));

  return Math.max(0, digitsBeforeCaret.length - 1);
}

export function getCaretPositionForNationalDigitIndex(value: string, digitIndex: number) {
  if (digitIndex <= 0) {
    const openingBracketIndex = value.indexOf("(");

    return openingBracketIndex === -1 ? value.length : openingBracketIndex + 1;
  }

  let seenNationalDigits = 0;
  let skippedPrefixDigit = false;

  for (let index = 0; index < value.length; index += 1) {
    if (!/\d/.test(value[index])) {
      continue;
    }

    if (!skippedPrefixDigit) {
      skippedPrefixDigit = true;
      continue;
    }

    seenNationalDigits += 1;

    if (seenNationalDigits === digitIndex) {
      return index + 1;
    }
  }

  return value.length;
}

export function removeNationalDigitAt(value: string, digitIndex: number) {
  const prefix = value.trim().startsWith("+") ? "+7" : "8";
  const nationalDigits = getNationalDigits(value);
  const nextNationalDigits =
    nationalDigits.slice(0, digitIndex) + nationalDigits.slice(digitIndex + 1);

  return formatPhoneParts(prefix, nextNationalDigits);
}

export function getMaskDigitRemovalIndex(key: string, value: string, caretPosition: number) {
  if (key !== "Backspace" && key !== "Delete") {
    return null;
  }

  const isBackspace = key === "Backspace";
  const maskCharacterIndex = isBackspace ? caretPosition - 1 : caretPosition;
  const maskCharacter = value[maskCharacterIndex] ?? "";

  if (!maskCharacter || /\d/.test(maskCharacter)) {
    return null;
  }

  const nationalDigitCaretIndex = getNationalDigitCaretIndex(value, caretPosition);
  const digitIndex = isBackspace ? nationalDigitCaretIndex - 1 : nationalDigitCaretIndex;

  return digitIndex < 0 ? null : digitIndex;
}
