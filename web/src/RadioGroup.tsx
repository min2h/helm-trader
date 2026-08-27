type Option = { value: string; label: string; hint?: string };

export function RadioGroup({
  name,
  value,
  options,
  onChange,
}: {
  name: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
}) {
  return (
    <fieldset className="radio-group">
      <legend>{name}</legend>
      <div className="radio-options">
        {options.map((option) => (
          <label key={option.value} className={option.value === value ? "on" : ""}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={option.value === value}
              onChange={() => onChange(option.value)}
            />
            <span>
              {option.label}
              {option.hint ? <small>{option.hint}</small> : null}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
