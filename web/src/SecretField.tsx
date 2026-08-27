import { useState } from "react";

export function SecretField({
  label,
  value,
  onChange,
  hint,
  placeholder = "아직 없음",
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  hint?: string;
  placeholder?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <label>
      {label}
      <div className="secret-row">
        <input
          type={show ? "text" : "password"}
          autoComplete="off"
          spellCheck={false}
          value={value}
          placeholder={hint || placeholder}
          onChange={(event) => onChange(event.target.value)}
        />
        <button type="button" disabled={!value} onClick={() => setShow((prev) => !prev)}>
          {show ? "숨기기" : "보기"}
        </button>
      </div>
    </label>
  );
}
