import { useState } from "react";
import { formatDecimal, formatInt, parseAmount } from "./format";

export function NumberField({
  value,
  onChange,
  decimals = 0,
  min,
  max,
  placeholder,
}: {
  value: string;
  onChange: (next: string) => void;
  decimals?: number;
  min?: number;
  max?: number;
  placeholder?: string;
}) {
  const [focused, setFocused] = useState(false);
  const parsed = parseAmount(value);
  const invalid =
    value.trim() !== "" &&
    (parsed === null || (min != null && parsed < min) || (max != null && parsed > max));
  const shown = focused
    ? value.replace(/,/g, "")
    : parsed === null
      ? value
      : decimals > 0
        ? formatDecimal(parsed, decimals)
        : formatInt(parsed);

  return (
    <input
      className={invalid ? "invalid" : ""}
      inputMode="decimal"
      placeholder={placeholder}
      value={shown}
      onFocus={() => {
        setFocused(true);
        onChange(value.replace(/,/g, ""));
      }}
      onBlur={() => {
        setFocused(false);
        if (parsed !== null) onChange(String(parsed));
      }}
      onChange={(event) => onChange(event.target.value.replace(/[^\d.,-]/g, ""))}
    />
  );
}
