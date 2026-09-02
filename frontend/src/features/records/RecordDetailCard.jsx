/**
 * Read only presentation of one clinical entry.
 *
 * Shared by the patient timeline and the doctor record view so the clinical
 * fields are laid out identically for both roles (DRY).
 */
import { formatVisitDate, recordTypeLabel } from './recordTypes';

/** Clinical fields rendered in order, skipping any the doctor left blank. */
const SECTIONS = [
  { key: 'symptoms', label: 'Reported Symptoms' },
  { key: 'examination', label: 'Examination Findings' },
  { key: 'diagnosis', label: 'Diagnosis' },
  { key: 'treatment', label: 'Treatment and Advice' },
  { key: 'follow_up', label: 'Follow-up Plan' },
  { key: 'notes', label: 'Additional Notes' },
];

export default function RecordDetailCard({ record }) {
  return (
    <div
      style={{
        marginTop: 'var(--ju-space-4)',
        paddingTop: 'var(--ju-space-4)',
        borderTop: '1px solid var(--ju-border)',
        display: 'grid',
        gap: 'var(--ju-space-4)',
      }}
    >
      <div>
        <span className="ju-kpi__label">Visit</span>
        <p style={{ margin: 0 }}>
          {formatVisitDate(record.visit_date)} · {recordTypeLabel(record.record_type)} · recorded by{' '}
          {record.doctor_name}
        </p>
      </div>

      {SECTIONS.filter((section) => record[section.key]).map((section) => (
        <div key={section.key}>
          <span className="ju-kpi__label">{section.label}</span>
          <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{record[section.key]}</p>
        </div>
      ))}
    </div>
  );
}
