/**
 * Labelled form control used by every JU_FIX form.
 *
 * The approved UI standard requires a visible label on every input, an asterisk
 * on required fields, inline validation text and a 48px control height.
 */
export default function FormField({
  label,
  name,
  value,
  onChange,
  type = 'text',
  required = false,
  error = '',
  help = '',
  placeholder = '',
  disabled = false,
  options = null,
  rows = 0,
  min,
  max,
}) {
  const fieldId = `field-${name}`;
  const describedBy = error ? `${fieldId}-error` : help ? `${fieldId}-help` : undefined;
  const controlClass = `ju-field__control${error ? ' ju-field__control--error' : ''}`;

  const shared = {
    id: fieldId,
    name,
    value: value ?? '',
    onChange,
    disabled,
    required,
    'aria-invalid': Boolean(error),
    'aria-describedby': describedBy,
    className: controlClass,
  };

  return (
    <div className="ju-field">
      <label className="ju-field__label" htmlFor={fieldId}>
        {label}
        {required && (
          <span className="ju-field__required" aria-hidden="true">
            *
          </span>
        )}
      </label>

      {options ? (
        <select {...shared}>
          <option value="">Select an option</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : rows > 0 ? (
        <textarea {...shared} rows={rows} placeholder={placeholder} />
      ) : (
        <input {...shared} type={type} placeholder={placeholder} min={min} max={max} />
      )}

      {help && !error && (
        <span className="ju-field__help" id={`${fieldId}-help`}>
          {help}
        </span>
      )}
      {error && (
        <span className="ju-field__error" id={`${fieldId}-error`} role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
